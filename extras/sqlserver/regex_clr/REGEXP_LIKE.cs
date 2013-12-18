using System;
using System.Data.SqlTypes;
using System.Text.RegularExpressions;
using Microsoft.SqlServer.Server;

public partial class UserDefinedFunctions
{
	private const RegexOptions DefaultRegExOptions =
		RegexOptions.IgnorePatternWhitespace | RegexOptions.Singleline;

	[SqlFunction(IsDeterministic = true, IsPrecise = true)]
    public static SqlInt32 REGEXP_LIKE(
        [SqlFacet(IsNullable = true, MaxSize = -1)]SqlString input, 
        [SqlFacet(IsNullable = true, MaxSize = -1)]SqlString pattern, 
        SqlInt32 caseSensitive)
	{
        if (input.IsNull || pattern.IsNull)
        {
            return 0;
        }

		RegexOptions options = DefaultRegExOptions;
		if (caseSensitive==0)
		{
		    options |= RegexOptions.IgnoreCase;
		}

		return Regex.IsMatch(input.Value, pattern.Value, options) ? 1 : 0;
	}
}