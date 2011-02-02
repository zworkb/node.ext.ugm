from node.aliasing import DictAliaser
from node.base import AbstractNode
from node.bbb import AttributedNode
from node.parts import AliasAttrs
from plumber import Part
from plumber import extend
from zope.interface import implements


class Principal(Part):
    """Turns a node into a principal
    """
    @extend
    @property
    def id(self):
        return self.__name__

    @extend
    def __repr__(self):
        return "<%s '%s'>" % (
                self.__class__.__name__.split('.')[-1],
                unicode(self.id).encode('ascii', 'replace'),
                )

    @extend
    def __iter__(self):
        return iter([])


class User(Principal):
    """Turns a node into a user
    """
    @extend
    @property
    def login(self):
        return self.attrs['login']

    @extend
    def authenticate(self, pw):
        return bool(self.__parent__.authenticate(id=self.id, pw=pw))

    @extend
    def passwd(self, oldpw, newpw):
        self.__parent__.passwd(id=self.id, oldpw=oldpw, newpw=newpw)


class Group(Principal):
    """Turns a node into a group
    """


class Principals(AbstractNode):
    """Turn a nodespace into a source of principals

    XXX: Should be based on a LazyNode to cache principal objects
    """
    principal_factory = None

    def __init__(self, context, principal_attrmap=None):
        self.context = context
        # XXX: it seems currently an aliaser is needed any way, is that good?
        self.principal_attrmap = principal_attrmap
        self.principal_attraliaser = DictAliaser(principal_attrmap)

    @property
    def __name__(self):
        return self.context.__name__

    # principals have ids
    @property
    def ids(self):
        return self.context.keys

    def __delitem__(self, key):
        del self.context[key]

    def __getitem__(self, key):
        # XXX: should use lazynodes caching, for now:
        # users['foo'] is not users['foo']
        principal = self.principal_factory(
                self.context[key],
                attraliaser=self.principal_attraliaser
                )
        principal.__name__ = self.context[key].__name__
        principal.__parent__ = self
        return principal

    def __iter__(self):
        return self.context.__iter__()

    def __setitem__(self, name, vessel):
        try:
            attrs = vessel.nodespaces['__attrs__']
        except KeyError:
            raise ValueError(u"Attributes need to be set.")

        nextvessel = AttributedNode()
        nextvessel.__name__ = name
        principal = self.principal_factory(
                nextvessel,
                attraliaser=self.principal_attraliaser
                )
        principal.__name__ = name
        principal.__parent__ = self
        # XXX: we could cache here, given that we are based on a LazyNode or
        # similar
        for key, val in attrs.iteritems():
            principal.attrs[key] = val
        self.context[name] = nextvessel

    def _alias_dict(self, dct):
        if dct is None:
            return None
        # this code does not work if multiple keys map to same value
        #alias = self.principal_attraliaser.alias
        #aliased_dct = dict(
        #        [(alias(key), val) for key, val in dct.iteritems()]
        #        )
        #return aliased_dct
        # XXX: maybe some generalization in aliaser needed
        ret = dict()
        for key, val in self.principal_attraliaser.iteritems():
            for k, v in dct.iteritems():
                if val == k:
                    ret[key] = v
        return ret

    def _unalias_list(self, lst):
        if lst is None:
            return None
        unalias = self.principal_attraliaser.unalias
        return [unalias(x) for x in lst]

    def _unalias_dict(self, dct):
        if dct is None:
            return None
        unalias = self.principal_attraliaser.unalias
        unaliased_dct = dict(
                [(unalias(key), val) for key, val in dct.iteritems()]
                )
        return unaliased_dct

    def search(self, criteria=None, attrlist=None, exact_match=False,
            or_search=False):
        # XXX: stripped down for now, compare to LDAPNode.search
        # XXX: are single values always lists in results?
        #      is this what we want?
        results = self.context.search(
                criteria=self._unalias_dict(criteria),
                attrlist=self._unalias_list(attrlist),
                exact_match=exact_match,
                or_search=or_search,
                )
        if attrlist is None:
            return results
        aliased_results = \
                [(id, self._alias_dict(attrs)) for id, attrs in results]
        return aliased_results
