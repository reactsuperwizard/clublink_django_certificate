from jinja2 import lexer, nodes
from jinja2.ext import Extension


class SharedSession(Extension):
    # This is to inject https://github.com/ViktorStiskala/django-shared-session into stupid jinja

    tags = set(['shared_session_loader'])

    def _load_shared_session(self, context):
        # print(context)
        # import pdb; pdb.set_trace();

        from clublink.base.utils import CustomLoaderNode as LoaderNode

        data = LoaderNode().render(context)
        return data

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        # token = parser.stream.expect(lexer.TOKEN_STRING)
        context = nodes.ContextReference()

        call = self.call_method('_load_shared_session', [context], lineno=lineno)
        final = nodes.Output([call], lineno=lineno)
        return final

# Example from https://github.com/MoritzS/jinja2-django-tags/blob/master/jdj_tags/extensions.py

# class DjangoStatic(Extension):
#     """
#     Implements django's `{% static %}` tag::
#         My static file: {% static 'my/static.file' %}
#         {% static 'my/static.file' as my_file %}
#         My static file in a var: {{ my_file }}
#     """
#     tags = set(['static'])

#     def _static(self, path):
#         return django_static(path)

#     def parse(self, parser):
#         lineno = next(parser.stream).lineno
#         token = parser.stream.expect(lexer.TOKEN_STRING)
#         path = nodes.Const(token.value)
#         call = self.call_method('_static', [path], lineno=lineno)

#         token = parser.stream.current
#         if token.test('name:as'):
#             next(parser.stream)
#             as_var = parser.stream.expect(lexer.TOKEN_NAME)
#             as_var = nodes.Name(as_var.value, 'store', lineno=as_var.lineno)
#             return nodes.Assign(as_var, call, lineno=lineno)
#         else:
#             return nodes.Output([call], lineno=lineno)
