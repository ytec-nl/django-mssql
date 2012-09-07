from django.db.models.sql import compiler
import datetime
import re


# query_class returns the base class to use for Django queries.
# The custom 'SqlServerQuery' class derives from django.db.models.sql.query.Query
# which is passed in as "QueryClass" by Django itself.
#
# SqlServerQuery overrides:
# ...insert queries to add "SET IDENTITY_INSERT" if needed.
# ...select queries to emulate LIMIT/OFFSET for sliced queries.

_re_order_limit_offset = re.compile(
    r'(?:ORDER BY\s+(.+?))?\s*(?:LIMIT\s+(\d+))?\s*(?:OFFSET\s+(\d+))?$')

# Pattern to find the quoted column name at the end of a field specification
_re_pat_col = re.compile(r"\[([^[]+)\]$")

# Pattern to find each of the parts of a column name (extra_select, table, field)
_re_pat_col_parts = re.compile(
    r'(?:' +
    r'(\([^\)]+\))\s+as\s+' +
    r'|(\[[^[]+\])\.' +
    r')?' +
    r'\[([^[]+)\]$',
    re.IGNORECASE
)

# Pattern used in column aliasing to find sub-select placeholders
_re_col_placeholder = re.compile(r'\{_placeholder_(\d+)\}')

def _break(s, find):
    """Break a string s into the part before the substring to find, 
    and the part including and after the substring."""
    i = s.find(find)
    return s[:i], s[i:]

def _get_order_limit_offset(sql):
    return _re_order_limit_offset.search(sql).groups()
    
def _remove_order_limit_offset(sql):
    return _re_order_limit_offset.sub('',sql).split(None, 1)[1]

class SQLCompiler(compiler.SQLCompiler):
    def resolve_columns(self, row, fields=()):
        # If the results are sliced, the resultset will have an initial 
        # "row number" column. Remove this column before the ORM sees it.
        if getattr(self, '_using_row_number', False):
            row = row[1:]
       
        values = []
        index_extra_select = len(self.query.extra_select.keys())
        for value, field in map(None, row[index_extra_select:], fields):
            if field:
                internal_type = field.get_internal_type()
                if internal_type == 'DateField' and isinstance(value, datetime.datetime):
                    value = value.date()
                elif internal_type == 'TimeField' and isinstance(value, datetime.datetime):
                    value = value.time()
            values.append(value)

        return row[:index_extra_select] + tuple(values)

    def _fix_aggregates(self):
        """
        MSSQL doesn't match the behavior of the other backends on a few of
        the aggregate functions; different return type behavior, different
        function names, etc.
        
        MSSQL's implementation of AVG maintains datatype without proding. To
        match behavior of other django backends, it needs to not drop remainders.
        E.g. AVG([1, 2]) needs to yield 1.5, not 1
        """
        if self.connection.cast_avg_to_float:
            for alias, aggregate in self.query.aggregate_select.items():
                if aggregate.sql_function == 'AVG':
                    # Embed the CAST in the template on this query to
                    # maintain multi-db support.
                    self.query.aggregate_select[alias].sql_template = \
                        '%(function)s(CAST(%(field)s AS FLOAT))'
                # translate StdDev function names
                elif aggregate.sql_function == 'STDDEV_SAMP':
                    self.query.aggregate_select[alias].sql_function = 'STDEV'
                elif aggregate.sql_function == 'STDDEV_POP':
                    self.query.aggregate_select[alias].sql_function = 'STDEVP'
                # translate Variance function names
                elif aggregate.sql_function == 'VAR_SAMP':
                    self.query.aggregate_select[alias].sql_function = 'VAR'
                elif aggregate.sql_function == 'VAR_POP':
                    self.query.aggregate_select[alias].sql_function = 'VARP'

    def as_sql(self, with_limits=True, with_col_aliases=False):
        self._fix_aggregates()
        
        self._using_row_number = False
        
        # Get out of the way if we're not a select query or there's no limiting involved.
        check_limits = with_limits and (self.query.low_mark or self.query.high_mark is not None)
        if not check_limits:
            return super(SQLCompiler, self).as_sql(with_limits, with_col_aliases)

        raw_sql, fields = super(SQLCompiler, self).as_sql(False, with_col_aliases)
        
        # Check for high mark only and replace with "TOP"
        if self.query.high_mark is not None and not self.query.low_mark:
            _select = 'SELECT'
            if self.query.distinct:
                _select += ' DISTINCT'
            
            sql = re.sub(r'(?i)^{0}'.format(_select), '{0} TOP {1}'.format(_select, self.query.high_mark), raw_sql, 1)
            return sql, fields
            
        # Else we have limits; rewrite the query using ROW_NUMBER()
        self._using_row_number = True

        order, limit_ignore, offset_ignore = _get_order_limit_offset(raw_sql)
        
        qn = self.connection.ops.quote_name
        
        inner_table_name = qn('AAAA')

        # Using ROW_NUMBER requires an ordering
        if order is None:
            meta = self.query.get_meta()                
            column = meta.pk.db_column or meta.pk.get_attname()
            order = '{0}.{1} ASC'.format(inner_table_name, qn(column))
        else:
            # remap order for injected subselect
            new_order = []
            for x in order.split(','):
                if x.find('.') != -1:
                    tbl, col = x.rsplit('.', 1)
                else:
                    col = x
                new_order.append('{0}.{1}'.format(inner_table_name, col))
            order = ', '.join(new_order)
        
        where_row_num = '{0} < _row_num'.format(self.query.low_mark)
        if self.query.high_mark:
            where_row_num += ' and _row_num <= {0}'.format(self.query.high_mark)
            
        # Lop off ORDER... and the initial "SELECT"
        inner_select = _remove_order_limit_offset(raw_sql)
        outer_fields, inner_select = self._alias_columns(inner_select)

        # map a copy of outer_fields for injected subselect
        f = []
        for x in outer_fields.split(','):
            i = x.find(' AS ')
            if i != -1:
                x = x[i+4:]
            if x.find('.') != -1:
                tbl, col = x.rsplit('.', 1)
            else:
                col = x
            f.append('{0}.{1}'.format(inner_table_name, col.strip()))
        
        
        # inject a subselect to get around OVER requiring ORDER BY to come from FROM
        inner_select = '{fields} FROM ( SELECT {inner} ) AS {inner_as}'.format(
            fields=', '.join(f),
            inner=inner_select,
            inner_as=inner_table_name,
        )
        
        sql = "SELECT _row_num, {outer} FROM ( SELECT ROW_NUMBER() OVER ( ORDER BY {order}) as _row_num, {inner}) as QQQ where {where}".format(
            outer=outer_fields,
            order=order,
            inner=inner_select,
            where=where_row_num,
        )
        
        return sql, fields

    def _alias_columns(self, sql):
        """Return tuple of SELECT and FROM clauses, aliasing duplicate column names."""
        qn = self.connection.ops.quote_name
        
        outer = list()
        inner = list()
        names_seen = list()
        
        # replace all parens with placeholders
        paren_depth, paren_buf = 0, ['']
        parens, i = {}, 0
        for ch in sql:
            if ch == '(':
                i += 1
                paren_depth += 1
                paren_buf.append('')
            elif ch == ')':
                paren_depth -= 1
                key = '_placeholder_{0}'.format(i)
                buf = paren_buf.pop()
                
                # store the expanded paren string
                parens[key] = buf.format(**parens)
                paren_buf[paren_depth] += '({' + key + '})'
            else:
                paren_buf[paren_depth] += ch
    
        def _replace_sub(col):
            """Replace all placeholders with expanded values"""
            while True:
                m = _re_col_placeholder.search(col)
                if m:
                    try:
                        key = '_placeholder_{0}'.format(
                            int(m.group(1))
                        )
                        col = col.format(**{
                            key : parens[key]
                        })
                    except:
                        # not a substituted value
                        break
                else:
                    break
            return col
    
        temp_sql = ''.join(paren_buf)
    
        select_list, from_clause = _break(temp_sql, ' FROM [')
            
        for col in [x.strip() for x in select_list.split(',')]:
            match = _re_pat_col.search(col)
            if match:
                col_name = match.group(1)
                col_key = col_name.lower()

                if col_key in names_seen:
                    alias = qn('{0}___{1}'.format(col_name, names_seen.count(col_key)))
                    outer.append(alias)
            
                    col = _replace_sub(col)
            
                    inner.append('{0} as {1}'.format(col, alias))
                else:
                    replaced = _replace_sub(col)
                            
                    outer.append(qn(col_name))
                    inner.append(replaced)
    
                names_seen.append(col_key)
            else:
                raise Exception('Unable to find a column name when parsing SQL: {0}'.format(col))

        return ', '.join(outer), ', '.join(inner) + from_clause.format(**parens)

class SQLInsertCompiler(compiler.SQLInsertCompiler, SQLCompiler):
    def as_sql(self, *args, **kwargs):
        # Fix for Django ticket #14019
        if not hasattr(self, 'return_id'):
            self.return_id = False

        result = super(SQLInsertCompiler, self).as_sql(*args, **kwargs)
        if isinstance(result, list):
            # Django 1.4 wraps return in list
            return [self._fix_insert(x[0], x[1]) for x in result]
        
        sql, params = result
        return self._fix_insert(sql, params)

    def _fix_insert(self, sql, params):
        """
        Wrap the passed SQL with IDENTITY_INSERT statements and apply
        other necessary fixes.
        """
        meta = self.query.get_meta()
        
        if meta.has_auto_field:
            if hasattr(self.query, 'fields'):
                # django 1.4 replaced columns with fields
                fields = self.query.fields
                auto_field = meta.auto_field
            else:
                # < django 1.4
                fields = self.query.columns
                auto_field = meta.auto_field.db_column or meta.auto_field.column
    
            auto_in_fields = auto_field in fields
    
            quoted_table = self.connection.ops.quote_name(meta.db_table)
            if not fields or (auto_in_fields and len(fields) == 1 and not params):
                # convert format when inserting only the primary key without 
                # specifying a value
                sql = 'INSERT INTO {0} DEFAULT VALUES'.format(
                    quoted_table
                )
                params = []
            elif auto_in_fields:
                # wrap with identity insert
                sql = 'SET IDENTITY_INSERT {table} ON;{sql};SET IDENTITY_INSERT {table} OFF'.format(
                    table=quoted_table,
                    sql=sql,
                )

        return sql, params

class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    pass

class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    pass

class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SQLCompiler):
    def as_sql(self, qn=None):
        self._fix_aggregates()
        return super(SQLAggregateCompiler, self).as_sql(qn=qn)

class SQLDateCompiler(compiler.SQLDateCompiler, SQLCompiler):
    pass
