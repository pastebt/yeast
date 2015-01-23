import tpl


class check_and_warn(object):
    def __init__(self, item_name, msg_sel):
        """
        item_name is form item name
        msg_sel is message node select string
        """
        self.item_name, self.msg_sel = item_name, msg_sel

    def __call__(self, func):
        self.func = func
        return self

    def __get__(self, obj, klass):
        def newfunc(*args):
            return self.func(obj, *args)
        return newfunc
 

class form_meta(type):
    def __new__(mcs, name, bases, dicti):
        dat = {}
        for d, v in dicti.items():
            if isinstance(v, check_and_warn):
                dat[v.item_name] = v
        dicti['name_func_map'] = dat
        return type.__new__(mcs, name, bases, dicti)


class Form(object):
    """
    This is a form processer, It create from a form node,
    validate input, if something wrong, return builded form.
    Decorate a checking function with node name and message
    selector. And checking function return warning message
    or empty if every thing OK

    @check_and_warn('username', 'em#username')
    def check_user_name(self, value, node):
        print 'Form.check_user_name'
        return ''
    """
    __metaclass__ = form_meta

    def __init__(self, form=None):
        self.form_node = form

    def set_node_value(self, node, value):
        if node.tag == 'input':
            node['value'] = value
        elif node.tag == 'textarea':
            node.set_inner_text(value)

    def get_validated(self, req_input, names):
        ret = {}
        for name in names:
            v = req_input.getfirst(name)
            if v is not None and name in self.name_func_map:
                msg = self.name_func_map[name].func(self, v, None)
                if msg:
                    continue
            ret[name] = v
        return ret

    def validate_and_update(self, req_input):
        """ req_input is a FieldStorage """
        items = self.form_node('input,select,file,textarea')
        ret = []
        for item in items:
            name = item.get('name')
            if not name:
                continue
            if name not in self.name_func_map:
                continue
            v = req_input.getfirst(name, '')
            node = self.form_node('[name="%s"]' % name)[0]
            self.set_node_value(node, v)
            caw = self.name_func_map[name]
            msg = caw.func(self, v, node)
            #print msg
            if not msg:
                continue
            if caw.msg_sel:
                if isinstance(caw.msg_sel, tpl.Node):
                    n = caw.msg_sel
                else:
                    n = self.form_node(caw.msg_sel)[0]
                n.set_inner_text(msg)
                ret.append(n)
            else:
                ret.append(None)
        return ret
