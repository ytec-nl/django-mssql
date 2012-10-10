import urllib
from docutils import nodes, utils
from sphinx import addnodes, roles, __version__ as sphinx_ver

# setup function to register the extension
def setup(app):
    app.add_config_value('django_ticket_base_url', 'https://code.djangoproject.com/ticket/', 'env')
    app.add_role('djangoticket', make_django_ticket_link)

    app.add_config_value('mssql_ticket_base_url', 'https://bitbucket.org/Manfre/django-mssql/issue/', 'env')
    app.add_role('issue', make_mssql_ticket_link)

    app.add_crossref_type(
        directivename = "setting",
        rolename      = "setting",
        indextemplate = "pair: %s; setting",
    )

def make_ticket_link(prefix, base_url, name, rawtext, text, lineno, inliner, options={}, content=[]):
    try:
        issue_num = int(text)
        if issue_num < 1:
            raise ValueError
    except ValueError:
        msg = inliner.reporter.error(
            '{0} issue number must be a number greater than or equal to 1; "{1}" is invalid.'.format(
                type_, text, line=lineno
            )
        )
        prb = inline.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    ref = base_url.rstrip('/') + '/' + urllib.quote(text, safe='')
    node = nodes.reference(rawtext, '{0} #{1}'.format(prefix, utils.unescape(text)), refuri=ref, **options)
    return [node],[]

def make_django_ticket_link(name, rawtext, text, lineno, inliner, options={}, content=[]):
    env = inliner.document.settings.env
    base_url =  env.config.django_ticket_base_url
    return make_ticket_link('Django ticket', base_url, name, rawtext, text, lineno, inliner, options, content)

def make_mssql_ticket_link(name, rawtext, text, lineno, inliner, options={}, content=[]):
    env = inliner.document.settings.env
    base_url =  env.config.mssql_ticket_base_url
    return make_ticket_link('django-mssql issue', base_url, name, rawtext, text, lineno, inliner, options, content)
