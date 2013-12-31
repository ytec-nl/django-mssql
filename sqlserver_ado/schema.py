import datetime
from django.utils import encoding, six

try:
    from django.db.backends.schema import BaseDatabaseSchemaEditor, logger
except ImportError:
    # Stub for newly added class
    class BaseDatabaseSchemaEditor(object):
        pass
    import logging
    logger = logging.getLogger('mssql')


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):
    sql_rename_table = "sp_rename '%(old_table)s', '%(new_table)s'"
    sql_delete_table = "DROP TABLE %(table)s"

    sql_create_column = "ALTER TABLE %(table)s ADD %(column)s %(definition)s"
    sql_alter_column_type = "ALTER COLUMN %(column)s %(type)s"
    sql_alter_column_null = "ALTER COLUMN %(column)s %(type)s NULL"
    sql_alter_column_not_null = "ALTER COLUMN %(column)s %(type)s NOT NULL"
    # sql_alter_column_default = "ALTER COLUMN %(column)s ADD CONSTRAINT %(constraint_name)s DEFAULT %(default)s"
    sql_alter_column_default = "ADD CONSTRAINT %(constraint_name)s DEFAULT %(default)s FOR %(column)s"
    sql_alter_column_no_default = "ALTER COLUMN %(column)s DROP CONSTRAINT %(constraint_name)s"
    sql_delete_column = "ALTER TABLE %(table)s DROP COLUMN %(column)s"
    sql_rename_column = "sp_rename '%(table)s.%(old_column)s', '%(new_column)s', 'COLUMN'"

    sql_create_fk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s FOREIGN KEY (%(column)s) REFERENCES %(to_table)s (%(to_column)s)"

    sql_delete_index = "DROP INDEX %(name)s ON %(table)s"

    def alter_db_table(self, model, old_db_table, new_db_table):
        # sp_rename requires that objects not be quoted because they are string literals
        self.execute(self.sql_rename_table % {
            "old_table": old_db_table,
            "new_table": new_db_table,
        })

    def delete_model(self, model):
        # Drop all inbound FKs before dropping table
        for rel in model._meta.get_all_related_objects():
            rel_fk_names = self._constraint_names(rel.model, [rel.field.column], foreign_key=True)
            for fk_name in rel_fk_names:
                self.execute(
                    self.sql_delete_fk % {
                        "table": self.quote_name(rel.model._meta.db_table),
                        "name": fk_name,
                    }
                )
        super(DatabaseSchemaEditor, self).delete_model(model)


    def delete_db_column(self, model, column):
        # drop all of the column constraints to avoid the database blocking the column removal
        drop_column_constraints_sql = """
DECLARE @sql nvarchar(max)
WHILE 1=1
BEGIN
    SELECT TOP 1 @sql = N'ALTER TABLE [%(table)s] DROP CONSTRAINT [' + dc.NAME + N']'
    FROM sys.default_constraints dc
        JOIN sys.columns c ON c.default_object_id = dc.object_id
    WHERE 
        dc.parent_object_id = OBJECT_ID('%(table)s')
        AND c.name = N'%(column)s'
    IF @@ROWCOUNT = 0 BREAK
    EXEC (@sql)
END""" %    {
                'table': model._meta.db_table,
                'column': column,
            }

        self.execute(drop_column_constraints_sql)
        super(DatabaseSchemaEditor, self).delete_db_column(model, column)

    def rename_db_column(self, model, old_db_column, new_db_column, new_type):
        """
        Renames a column on a table.
        """
        self.execute(self.sql_rename_column % {
            "table": self.quote_name(model._meta.db_table),
            "old_column": self.quote_name(old_db_column),
            "new_column": new_db_column, # not quoting because it's a string literal
            "type": new_type,
        })

    def _alter_db_column_sql(self, model, column, alteration=None, values={}, fragment=False, params=None):
        if alteration == 'default':
            # remove old default constraint
            remove_actions = self._alter_db_column_sql(model, column, alteration='no_default', values=values,
                fragment=fragment, params=params)
            # now add the new one
            actions = super(DatabaseSchemaEditor, self)._alter_db_column_sql(model, column, alteration,
                values, fragment, params)
            return (
                remove_actions[0] + actions[0], # sql
                remove_actions[1] + actions[1]  # params
            )
        if alteration == 'no_default':
            # only post_actions to delete the default constraint
            sql, params = self._drop_default_column(model, column)
            return [([], [])], [(sql, params)]
        else:
            return super(DatabaseSchemaEditor, self)._alter_db_column_sql(model, column, alteration,
                values, fragment, params)

    def _drop_default_column(self, model, column):
        """
        Drop the default constraint for a column on a model.
        """
        sql = '''
DECLARE @sql nvarchar(max)
WHILE 1=1
BEGIN
    SELECT TOP 1 @sql = N'ALTER TABLE %(table)s DROP CONSTRAINT [' + dc.NAME + N']'
    FROM sys.default_constraints dc
    JOIN sys.columns c
        ON c.default_object_id = dc.object_id
    WHERE
        dc.parent_object_id = OBJECT_ID(%%s)
    AND c.name = %%s
    IF @@ROWCOUNT = 0 BREAK
    EXEC (@sql)
END''' % {'table': model._meta.db_table}
        params = [model._meta.db_table, column]
        return sql, params

    def prepare_default(self, value):
        return "%s" % self._quote_parameter(value), []

    def _quote_parameter(self, value):
        if isinstance(value, (datetime.date, datetime.time, datetime.datetime)):
            return "'%s'" % value
        elif isinstance(value, six.string_types):
            return "'%s'" % value
        elif isinstance(value, bool):
            return "1" if value else "0"
        elif value is None:
            return "NULL"
        else:
            return str(value)

    # def execute(self, sql, params=[]):
    #     """
    #     Executes the given SQL statement, with optional parameters.
    #     """
    #     if not sql:
    #         return
    #     # Get the cursor
    #     cursor = self.connection.cursor()
    #     # Log the command we're running, then run it
    #     logger.debug("%s; (params %r)" % (sql, params))
    #     if self.collect_sql:
    #         c = (sql % tuple(map(self._quote_parameter, params))) + ";"
    #         print 'collected sql=', c
    #         self.collected_sql.append(c)

    #     else:
    #         print 'sql=', sql
    #         print 'params=', params
    #         cursor.execute(sql, params)
