import pytest
from rodi import (
    ServiceCollection,
    CircularDependencyException,
    OverridingServiceException,
    UnsupportedUnionTypeException,
    MissingTypeException,
    GetServiceContext,
    to_standard_param_name
)
from rodi.tests.examples import (
    ICatsRepository,
    GetCatRequestHandler,
    CatsController,
    IRequestContext,
    RequestContext,
    Cat,
    Foo,
    ServiceSettings,
    InMemoryCatsRepository,
    FooDBContext,
    FooDBCatsRepository,
    IdGetter,
    A,
    B,
    C,
    P,
    R,
    W,
    X,
    Y,
    Z,
    Jing,
    Jang,
    ICircle,
    Circle,
    Shape,
    TrickyCircle,
    TypeWithOptional,
    ResolveThisByParameterName,
    IByParamName,
    FooByParamName
)


def arrange_cats_example():
    services = ServiceCollection()
    services.add_transient(ICatsRepository, FooDBCatsRepository)
    services.add_scoped(IRequestContext, RequestContext)
    services.add_exact_transient(GetCatRequestHandler)
    services.add_exact_transient(CatsController)
    services.add_instance(ServiceSettings('foodb:example;something;'))
    services.add_exact_transient(FooDBContext)
    return services


@pytest.mark.parametrize('value,expected_result', (
    ('CamelCase', 'camel_case'),
    ('HTTPResponse', 'http_response'),
    ('ICatsRepository', 'icats_repository'),
    ('Cat', 'cat'),
    ('UFO', 'ufo'),
))
def test_standard_param_name(value, expected_result):
    snaked = to_standard_param_name(value)
    assert snaked == expected_result


def test_singleton_by_instance():
    services = ServiceCollection()
    services.add_instance(Cat('Celine'))
    provider = services.build_provider()

    cat = provider.get(Cat)

    assert cat is not None
    assert cat.name == "Celine"


def test_transient_by_type_without_parameters():
    services = ServiceCollection()
    services.add_transient(ICatsRepository, InMemoryCatsRepository)
    provider = services.build_provider()
    cats_repo = provider.get(ICatsRepository)

    assert isinstance(cats_repo, InMemoryCatsRepository)
    other_cats_repo = provider.get(ICatsRepository)

    assert isinstance(other_cats_repo, InMemoryCatsRepository)
    assert cats_repo is not other_cats_repo


def test_transient_by_type_with_parameters():
    services = ServiceCollection()
    services.add_transient(ICatsRepository, FooDBCatsRepository)

    # NB:
    services.add_instance(ServiceSettings('foodb:example;something;'))
    services.add_exact_transient(FooDBContext)
    provider = services.build_provider()

    cats_repo = provider.get(ICatsRepository)

    assert isinstance(cats_repo, FooDBCatsRepository)
    assert isinstance(cats_repo.context, FooDBContext)
    assert isinstance(cats_repo.context.settings, ServiceSettings)
    assert cats_repo.context.connection_string == 'foodb:example;something;'


def test_raises_for_overriding_service():
    services = ServiceCollection()
    services.add_transient(ICircle, Circle)

    with pytest.raises(OverridingServiceException) as context:
        services.add_singleton(ICircle, Circle)

    assert 'ICircle' in str(context.value)

    with pytest.raises(OverridingServiceException) as context:
        services.add_transient(ICircle, Circle)

    assert 'ICircle' in str(context.value)

    with pytest.raises(OverridingServiceException) as context:
        services.add_scoped(ICircle, Circle)

    assert 'ICircle' in str(context.value)


def test_raises_for_circular_dependency():
    services = ServiceCollection()
    services.add_transient(ICircle, Circle)

    with pytest.raises(CircularDependencyException) as context:
        services.build_provider()

    assert 'Circle' in str(context.value)


def test_raises_for_circular_dependency_with_dynamic_resolver():
    services = ServiceCollection()
    services.add_exact_transient(Jing)
    services.add_exact_transient(Jang)

    with pytest.raises(CircularDependencyException):
        services.build_provider()


def test_raises_for_deep_circular_dependency_with_dynamic_resolver():
    services = ServiceCollection()
    services.add_exact_transient(W)
    services.add_exact_transient(X)
    services.add_exact_transient(Y)
    services.add_exact_transient(Z)

    with pytest.raises(CircularDependencyException):
        services.build_provider()


def test_does_not_raise_for_deep_circular_dependency_with_one_factory():
    services = ServiceCollection()
    services.add_exact_transient(W)
    services.add_exact_transient(X)
    services.add_exact_transient(Y)

    def z_factory(_) -> Z:
        return Z(None)

    services.add_transient_by_factory(z_factory)

    provider = services.build_provider()

    w = provider.get(W)

    assert isinstance(w, W)
    assert isinstance(w.x, X)
    assert isinstance(w.x.y, Y)
    assert isinstance(w.x.y.z, Z)
    assert w.x.y.z.w is None


def test_circular_dependency_is_supported_by_factory():
    def get_jang(_) -> Jang:
        return Jang(None)

    services = ServiceCollection()
    services.add_exact_transient(Jing)
    services.add_transient_by_factory(get_jang)

    provider = services.build_provider()

    jing = provider.get(Jing)
    assert jing is not None
    assert isinstance(jing.jang, Jang)
    assert jing.jang.jing is None


def test_add_instance_allows_for_circular_classes():
    services = ServiceCollection()
    services.add_instance(Circle(Circle(None)))

    # NB: in this example, Shape requires a Circle
    services.add_exact_transient(Shape)
    provider = services.build_provider()

    circle = provider.get(Circle)
    assert isinstance(circle, Circle)

    shape = provider.get(Shape)

    assert isinstance(shape, Shape)
    assert shape.circle is circle


def test_add_instance_with_declared_type():
    services = ServiceCollection()
    services.add_instance(Circle(Circle(None)), declared_class=ICircle)
    provider = services.build_provider()

    icircle = provider.get(ICircle)
    assert isinstance(icircle, Circle)


def test_raises_for_optional_parameter():
    services = ServiceCollection()
    services.add_exact_transient(Foo)
    services.add_exact_transient(TypeWithOptional)

    with pytest.raises(UnsupportedUnionTypeException) as context:
        services.build_provider()

    assert 'foo' in str(context.value)


def test_raises_for_nested_circular_dependency():
    services = ServiceCollection()
    services.add_transient(ICircle, Circle)
    services.add_exact_transient(TrickyCircle)

    with pytest.raises(CircularDependencyException) as context:
        services.build_provider()

    assert 'Circle' in str(context.value)


def test_interdependencies():
    services = ServiceCollection()
    services.add_exact_transient(A)
    services.add_exact_transient(B)
    services.add_exact_transient(C)
    services.add_exact_transient(IdGetter)
    provider = services.build_provider()

    c = provider.get(C)

    assert isinstance(c, C)
    assert isinstance(c.a, A)
    assert isinstance(c.b, B)
    assert isinstance(c.b.a, A)


def test_transient_service():
    services = ServiceCollection()
    services.add_transient(ICatsRepository, InMemoryCatsRepository)
    provider = services.build_provider()

    cats_repo = provider.get(ICatsRepository)
    assert isinstance(cats_repo, InMemoryCatsRepository)

    other_cats_repo = provider.get(ICatsRepository)
    assert cats_repo is not other_cats_repo


def test_singleton_services():
    services = ServiceCollection()
    services.add_exact_singleton(IdGetter)
    provider = services.build_provider()

    with GetServiceContext() as context:
        a = provider.get(IdGetter, context)
        b = provider.get(IdGetter, context)
        c = provider.get(IdGetter, context)
    d = provider.get(IdGetter)

    assert a is b
    assert a is c
    assert b is c
    assert d is a


def test_transient_services():
    services = ServiceCollection()
    services.add_exact_transient(IdGetter)
    provider = services.build_provider()

    with GetServiceContext() as context:
        a = provider.get(IdGetter, context)
        b = provider.get(IdGetter, context)
        c = provider.get(IdGetter, context)
    d = provider.get(IdGetter)

    assert a is not b
    assert a is not c
    assert b is not c
    assert d is not a
    assert d is not b
    assert d is not c


def test_scoped_services():
    services = ServiceCollection()
    services.add_exact_scoped(IdGetter)
    provider = services.build_provider()

    with GetServiceContext() as context:
        a = provider.get(IdGetter, context)
        b = provider.get(IdGetter, context)
        c = provider.get(IdGetter, context)
    d = provider.get(IdGetter)

    assert a is b
    assert b is c
    assert a is not d
    assert b is not d


def test_resolution_by_parameter_name():
    services = ServiceCollection()
    services.add_transient(ICatsRepository, InMemoryCatsRepository)
    services.add_exact_transient(ResolveThisByParameterName)

    provider = services.build_provider()
    resolved = provider.get(ResolveThisByParameterName)

    assert resolved is not None

    assert isinstance(resolved, ResolveThisByParameterName)
    assert isinstance(resolved.cats_repository, InMemoryCatsRepository)


def test_resolve_singleton_by_parameter_name():
    services = ServiceCollection()
    services.add_transient(IByParamName, FooByParamName)

    singleton = Foo()
    services.add_instance(singleton)

    provider = services.build_provider()
    resolved = provider.get(IByParamName)

    assert resolved is not None

    assert isinstance(resolved, FooByParamName)
    assert resolved.foo is singleton


def test_service_collection_contains():
    services = ServiceCollection()
    services.add_exact_transient(Foo)

    assert Foo in services
    assert Cat not in services


def test_service_provider_contains():
    services = ServiceCollection()
    services.add_exact_transient(IdGetter)

    provider = services.build_provider()

    assert Foo not in provider
    assert IdGetter in provider


def test_exact_alias():
    services = arrange_cats_example()

    class UsingAlias:

        def __init__(self, example):
            self.cats_controller = example

    services.add_exact_transient(UsingAlias)

    # arrange an exact alias for UsingAlias class init parameter:
    services.set_alias('example', CatsController)

    provider = services.build_provider()
    u = provider.get(UsingAlias)

    assert isinstance(u, UsingAlias)
    assert isinstance(u.cats_controller, CatsController)
    assert isinstance(u.cats_controller.cat_request_handler, GetCatRequestHandler)


def test_additional_alias():
    services = arrange_cats_example()

    class UsingAlias:

        def __init__(self, example, settings):
            self.cats_controller = example
            self.settings = settings

    class AnotherUsingAlias:

        def __init__(self, cats_controller, service_settings):
            self.cats_controller = cats_controller
            self.settings = service_settings

    services.add_exact_transient(UsingAlias)
    services.add_exact_transient(AnotherUsingAlias)

    # arrange an exact alias for UsingAlias class init parameter:
    services.add_alias('example', CatsController)
    services.add_alias('settings', ServiceSettings)

    provider = services.build_provider()
    u = provider.get(UsingAlias)

    assert isinstance(u, UsingAlias)
    assert isinstance(u.settings, ServiceSettings)
    assert isinstance(u.cats_controller, CatsController)
    assert isinstance(u.cats_controller.cat_request_handler, GetCatRequestHandler)

    u = provider.get(AnotherUsingAlias)

    assert isinstance(u, AnotherUsingAlias)
    assert isinstance(u.settings, ServiceSettings)
    assert isinstance(u.cats_controller, CatsController)
    assert isinstance(u.cats_controller.cat_request_handler, GetCatRequestHandler)


def test_get_service_by_name_or_alias():
    services = arrange_cats_example()
    services.add_alias('k', CatsController)

    provider = services.build_provider()

    for name in {'CatsController', 'cats_controller', 'k'}:
        service = provider.get(name)

        assert isinstance(service, CatsController)
        assert isinstance(service.cat_request_handler, GetCatRequestHandler)
        assert isinstance(service.cat_request_handler.repo, FooDBCatsRepository)


def test_missing_service_returns_none():
    services = ServiceCollection()
    provider = services.build_provider()
    service = provider.get('not_existing')
    assert service is None


@pytest.mark.parametrize('method_name', [
    'add_singleton_by_factory',
    'add_transient_by_factory',
    'add_scoped_by_factory'
])
def test_add_singleton_by_factory_type_annotation(method_name):
    services = ServiceCollection()

    def factory(_) -> Cat:
        return Cat('Celine')

    method = getattr(services, method_name)

    method(factory)

    provider = services.build_provider()

    cat = provider.get(Cat)

    assert cat is not None
    assert cat.name == 'Celine'

    if method_name == 'add_singleton_by_factory':
        cat_2 = provider.get(Cat)
        assert cat_2 is cat

    if method_name == 'add_transient_by_factory':
        assert provider.get(Cat) is not cat
        assert provider.get(Cat) is not cat
        assert provider.get(Cat) is not cat

    if method_name == 'add_scoped_by_factory':
        with GetServiceContext() as context:
            cat_2 = provider.get(Cat, context)
            assert cat_2 is not cat

            assert provider.get(Cat, context) is cat_2
            assert provider.get(Cat, context) is cat_2
            assert provider.get(Cat, context) is cat_2


@pytest.mark.parametrize('method_name', [
    'add_singleton_by_factory',
    'add_transient_by_factory',
    'add_scoped_by_factory'
])
def test_add_singleton_by_factory_given_type(method_name):
    services = ServiceCollection()

    def factory(a):
        return Cat('Celine')

    method = getattr(services, method_name)

    method(factory, Cat)

    provider = services.build_provider()

    cat = provider.get(Cat)

    assert cat is not None
    assert cat.name == 'Celine'

    if method_name == 'add_singleton_by_factory':
        cat_2 = provider.get(Cat)
        assert cat_2 is cat

    if method_name == 'add_transient_by_factory':
        assert provider.get(Cat) is not cat
        assert provider.get(Cat) is not cat
        assert provider.get(Cat) is not cat

    if method_name == 'add_scoped_by_factory':
        with GetServiceContext() as context:
            cat_2 = provider.get(Cat, context)
            assert cat_2 is not cat

            assert provider.get(Cat, context) is cat_2
            assert provider.get(Cat, context) is cat_2
            assert provider.get(Cat, context) is cat_2


@pytest.mark.parametrize('method_name', [
    'add_singleton_by_factory',
    'add_transient_by_factory',
    'add_scoped_by_factory'
])
def test_add_singleton_by_factory_raises_for_missing_type(method_name):
    services = ServiceCollection()

    def factory(_):
        return Cat('Celine')

    method = getattr(services, method_name)

    with pytest.raises(MissingTypeException):
        method(factory)


def test_singleton_by_provider():
    services = ServiceCollection()
    services.add_exact_singleton(P)
    services.add_exact_transient(R)

    provider = services.build_provider()

    p = provider.get(P)
    r = provider.get(R)

    assert p is not None
    assert r is not None
    assert r.p is p


def test_singleton_by_provider_both_singletons():
    services = ServiceCollection()
    services.add_exact_singleton(P)
    services.add_exact_singleton(R)

    provider = services.build_provider()

    p = provider.get(P)
    r = provider.get(R)

    assert p is not None
    assert r is not None
    assert r.p is p

    r_2 = provider.get(R)
    assert r_2 is r