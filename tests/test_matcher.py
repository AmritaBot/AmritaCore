import asyncio

import pytest
from exceptiongroup import ExceptionGroup

from amrita_core.config import AmritaConfig
from amrita_core.hook.event import (
    BaseEvent,
    CompletionEvent,
    EventTypeEnum,
    PreCompletionEvent,
)
from amrita_core.hook.matcher import (
    Depends,
    DependsFactory,
    EventRegistry,
    Matcher,
    MatcherFactory,
)
from amrita_core.hook.on import on_completion, on_precompletion


class SpecException(ValueError): ...


class TestEvent(BaseEvent):
    """Test event class for unit tests."""

    def get_event_type(self) -> str:
        return "test_event"

    @property
    def event_type(self) -> str:
        return "test_event"


class TestDependsFactory:
    """Test DependsFactory class."""

    @pytest.mark.asyncio
    async def test_depends_factory_basic(self):
        """Test basic DependsFactory functionality."""

        async def dependency_func() -> str:
            return "test_value"

        factory = DependsFactory(dependency_func)
        result = await factory.resolve()
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_depends_factory_with_no_params(self):
        """Test DependsFactory with no parameters (most common case)."""

        async def dependency_func() -> str:
            return "no_params_value"

        factory = DependsFactory(dependency_func)
        result = await factory.resolve()
        assert result == "no_params_value"

    @pytest.mark.asyncio
    async def test_depends_factory_sync_function(self):
        """Test DependsFactory with synchronous function."""

        def sync_dependency() -> str:
            return "sync_value"

        factory = DependsFactory(sync_dependency)
        result = await factory.resolve()
        assert result == "sync_value"

    @pytest.mark.asyncio
    async def test_depends_factory_none_return(self):
        """Test DependsFactory that returns None."""

        async def none_dependency() -> None:
            return None

        factory = DependsFactory(none_dependency)
        result = await factory.resolve()
        assert result is None

    @pytest.mark.asyncio
    async def test_depends_factory_exception(self):
        """Test DependsFactory that raises exception."""

        async def error_dependency() -> str:
            raise ValueError("Test error")

        factory = DependsFactory(error_dependency)
        with pytest.raises(ValueError, match="Test error"):
            await factory.resolve()


class TestDependsDecorator:
    """Test Depends decorator function."""

    def test_depends_decorator_creation(self):
        """Test that Depends decorator creates DependsFactory."""

        async def test_dependency():
            return "dep_value"

        result = Depends(test_dependency)
        assert isinstance(result, DependsFactory)
        # Note: The internal attribute is _depency_func, not depency
        assert result._depency_func == test_dependency


class TestMatcherDecorators:
    """Test Matcher decorators."""

    def setup_method(self):
        """Clear event registry before each test."""
        EventRegistry()._event_handlers.clear()

    def teardown_method(self):
        """Clear event registry after each test."""
        EventRegistry()._event_handlers.clear()

    def test_on_event_decorator(self):
        """Test @on_event decorator registration."""
        matcher = Matcher("test_event", block=False)  # Set block=False for testing

        @matcher.handle()
        async def test_handler(event: TestEvent):
            pass

        registry = EventRegistry()
        handlers = registry.get_handlers("test_event")
        assert len(handlers) == 1
        assert matcher.priority in handlers  # default priority is 10
        assert len(handlers[matcher.priority]) == 1
        assert handlers[matcher.priority][0].function == test_handler

    def test_on_event_with_priority(self):
        """Test @on_event decorator with custom priority."""
        matcher = Matcher(
            "test_event", priority=5, block=False
        )  # Set block=False for testing

        @matcher.handle()
        async def test_handler(event: TestEvent):
            pass

        registry = EventRegistry()
        handlers = registry.get_handlers("test_event")
        assert 5 in handlers
        assert handlers[5][0].function == test_handler

    def test_on_precompletion_decorator(self):
        """Test @on_precompletion decorator."""

        matcher = on_precompletion(block=False)  # Set block=False for testing

        @matcher.handle()
        async def test_handler(event: PreCompletionEvent):
            pass

        registry = EventRegistry()
        handlers = registry.get_handlers(EventTypeEnum.BEFORE_COMPLETION)
        assert len(handlers[matcher.priority]) == 1

    def test_on_completion_decorator(self):
        """Test @on_completion decorator."""
        matcher = on_completion(block=False)  # Set block=False for testing

        @matcher.handle()
        async def test_handler(event: CompletionEvent):
            pass

        registry = EventRegistry()
        handlers = registry.get_handlers(EventTypeEnum.COMPLETION)
        assert len(handlers[matcher.priority]) == 1


class TestMatcherFactoryRuntimeResolve:
    """Test _do_runtime_resolve method."""

    def setup_method(self):
        """Setup test environment."""
        self.config = AmritaConfig()

    @pytest.mark.asyncio
    async def test_do_runtime_resolve_empty(self):
        """Test _do_runtime_resolve with no dependencies."""
        runtime_args = {}
        runtime_kwargs = {}
        args2update = []
        kwargs2update = {}
        session_args = []
        session_kwargs = {}
        exception_ignored = ()

        result = await MatcherFactory._do_runtime_resolve(
            runtime_args,
            runtime_kwargs,
            args2update,
            kwargs2update,
            session_args,
            session_kwargs,
            exception_ignored,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_do_runtime_resolve_kwargs_success(self):
        """Test _do_runtime_resolve with successful kwargs dependencies."""

        async def dep1() -> str:
            return "value1"

        async def dep2() -> str:
            return "value2"

        factory1 = DependsFactory(dep1)
        factory2 = DependsFactory(dep2)

        runtime_args = {}
        runtime_kwargs = {"key1": factory1, "key2": factory2}
        args2update = []
        kwargs2update = {}
        session_args = ["arg1", "arg2"]
        session_kwargs = {"session_key": "session_value"}
        exception_ignored = ()

        result = await MatcherFactory._do_runtime_resolve(
            runtime_args,
            runtime_kwargs,
            args2update,
            kwargs2update,
            session_args,
            session_kwargs,
            exception_ignored,
        )

        assert result is True
        assert kwargs2update == {"key1": "value1", "key2": "value2"}

    @pytest.mark.asyncio
    async def test_do_runtime_resolve_args_success(self):
        """Test _do_runtime_resolve with successful args dependencies."""

        async def dep1() -> str:
            return "arg_value1"

        async def dep2() -> str:
            return "arg_value2"

        factory1 = DependsFactory(dep1)
        factory2 = DependsFactory(dep2)

        runtime_args = {0: factory1, 2: factory2}
        runtime_kwargs = {}
        args2update = ["old1", "old2", "old3"]
        kwargs2update = {}
        session_args = ["session_arg1", "session_arg2"]
        session_kwargs = {"session_kw": "session_val"}
        exception_ignored = ()

        result = await MatcherFactory._do_runtime_resolve(
            runtime_args,
            runtime_kwargs,
            args2update,
            kwargs2update,
            session_args,
            session_kwargs,
            exception_ignored,
        )

        assert result is True
        assert args2update == ["arg_value1", "old2", "arg_value2"]

    @pytest.mark.asyncio
    async def test_do_runtime_resolve_none_result(self):
        """Test _do_runtime_resolve when dependency returns None."""

        async def none_dep() -> str | None:
            return None

        factory = DependsFactory(none_dep)

        runtime_args = {}
        runtime_kwargs = {"key": factory}
        args2update = []
        kwargs2update = {}
        session_args = []
        session_kwargs = {}
        exception_ignored = ()

        result = await MatcherFactory._do_runtime_resolve(
            runtime_args,
            runtime_kwargs,
            args2update,
            kwargs2update,
            session_args,
            session_kwargs,
            exception_ignored,
        )

        assert result is False
        assert kwargs2update == {}  # Should not be updated

    @pytest.mark.asyncio
    async def test_do_runtime_resolve_exception(self):
        """Test _do_runtime_resolve with exception in dependency."""

        async def error_dep() -> str:
            raise ValueError("Test error")

        factory = DependsFactory(error_dep)

        runtime_args = {}
        runtime_kwargs = {"key": factory}
        args2update = []
        kwargs2update = {}
        session_args = []
        session_kwargs = {}
        exception_ignored = ()

        # The exception should be caught and re-raised as ExceptionGroup
        with pytest.raises(ExceptionGroup) as exc_info:
            await MatcherFactory._do_runtime_resolve(
                runtime_args,
                runtime_kwargs,
                args2update,
                kwargs2update,
                session_args,
                session_kwargs,
                exception_ignored,
            )

        # Verify that the original exception is in the ExceptionGroup
        assert len(exc_info.value.exceptions) == 1
        assert isinstance(exc_info.value.exceptions[0], ValueError)
        assert str(exc_info.value.exceptions[0]) == "Test error"


class TestMatcherFactorySimpleRun:
    """Test _simple_run method."""

    def setup_method(self):
        """Setup test environment."""
        self.config = AmritaConfig()
        EventRegistry()._event_handlers.clear()

    def teardown_method(self):
        """Cleanup after test."""
        EventRegistry()._event_handlers.clear()

    @pytest.mark.asyncio
    async def test_simple_run_no_dependencies(self):
        """Test _simple_run with handler that has no dependencies."""
        call_count = 0

        matcher = Matcher("test_event", block=False)  # Set block=False

        @matcher.handle()
        async def test_handler(event: TestEvent, config: AmritaConfig):
            nonlocal call_count
            call_count += 1
            assert isinstance(event, TestEvent)
            assert config == self.config

        event = TestEvent()
        handlers = EventRegistry().get_handlers("test_event")

        result = await MatcherFactory._simple_run(
            handlers[matcher.priority], event, self.config, (), (), {}
        )

        assert result is True
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_simple_run_with_runtime_deps(self):
        """Test _simple_run with runtime dependencies from hook_kwargs."""
        received_deps = {}

        async def dep_func() -> str:
            return "runtime_value"

        matcher = Matcher("test_event", block=False)  # Set block=False

        @matcher.handle()
        async def test_handler(
            event: TestEvent, config: AmritaConfig, runtime_dep: str
        ):
            nonlocal received_deps
            received_deps["runtime_dep"] = runtime_dep

        event = TestEvent()
        handlers = EventRegistry().get_handlers("test_event")

        result = await MatcherFactory._simple_run(
            handlers[matcher.priority],
            event,
            self.config,
            (),
            (),
            {"runtime_dep": Depends(dep_func)},
        )

        assert result is True
        assert received_deps["runtime_dep"] == "runtime_value"

    @pytest.mark.asyncio
    async def test_simple_run_with_default_deps(self):
        """Test _simple_run with default dependencies in function signature."""
        received_deps = {}

        async def default_dep() -> str:
            return "default_value"

        matcher = Matcher("test_event", block=False)  # Set block=False

        @matcher.handle()
        async def test_handler(
            event: TestEvent,
            config: AmritaConfig,
            default_dep_param: str = Depends(default_dep),
        ):
            nonlocal received_deps
            received_deps["default_dep_param"] = default_dep_param

        event = TestEvent()
        handlers = EventRegistry().get_handlers("test_event")

        result = await MatcherFactory._simple_run(
            handlers[matcher.priority], event, self.config, (), (), {}
        )

        assert result is True
        assert received_deps["default_dep_param"] == "default_value"

    @pytest.mark.asyncio
    async def test_simple_run_runtime_deps_failure(self):
        """Test _simple_run when runtime deps fail to resolve."""

        async def failing_dep() -> str | None:
            return None

        matcher = Matcher("test_event", block=False)  # Set block=False

        @matcher.handle()
        async def test_handler(event: TestEvent, config: AmritaConfig, bad_dep: str):
            pass

        event = TestEvent()
        handlers = EventRegistry().get_handlers("test_event")

        with pytest.raises(RuntimeError, match="Runtime arguments cannot be resolved"):
            await MatcherFactory._simple_run(
                handlers[matcher.priority],
                event,
                self.config,
                (),
                (),
                {"bad_dep": Depends(failing_dep)},
            )

    @pytest.mark.asyncio
    async def test_simple_run_default_deps_failure(self):
        """Test _simple_run when default deps fail to resolve (should skip handler)."""
        call_count = 0

        async def failing_dep() -> str | None:
            return None

        matcher = Matcher("test_event", block=False)  # Set block=False

        @matcher.handle()
        async def test_handler(
            event: TestEvent, config: AmritaConfig, bad_dep: str = Depends(failing_dep)
        ):
            nonlocal call_count
            call_count += 1

        event = TestEvent()
        handlers = EventRegistry().get_handlers("test_event")

        result = await MatcherFactory._simple_run(
            handlers[matcher.priority], event, self.config, (), (), {}
        )

        assert result is True  # Should continue to next handler
        assert call_count == 0  # Handler should be skipped


class TestMatcherFactoryTriggerEvent:
    """Test trigger_event method."""

    def setup_method(self):
        """Setup test environment."""
        self.config = AmritaConfig()
        EventRegistry()._event_handlers.clear()

    def teardown_method(self):
        """Cleanup after test."""
        EventRegistry()._event_handlers.clear()

    @pytest.mark.asyncio
    async def test_trigger_event_basic(self):
        """Test basic trigger_event functionality."""
        call_count = 0

        matcher = Matcher("test_event", block=False)  # Set block=False

        @matcher.handle()
        async def test_handler(event: TestEvent, config: AmritaConfig):
            nonlocal call_count
            call_count += 1

        event = TestEvent()
        await MatcherFactory.trigger_event(event, self.config)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_trigger_event_with_hook_args_kwargs(self):
        """Test trigger_event with hook_args and hook_kwargs."""
        received_extra_kwargs = {}
        default_kw = {"extra_kw1": "value1", "extra_kw2": "value2"}

        matcher = Matcher("test_event", block=False)  # Set block=False

        @matcher.handle()
        async def test_handler(
            event: TestEvent,
            config: AmritaConfig,
            extra_kw1: str,
            extra_kw2: str,
        ):
            nonlocal received_extra_kwargs
            received_extra_kwargs.update(
                {"extra_kw1": extra_kw1, "extra_kw2": extra_kw2}
            )

        event = TestEvent()
        await MatcherFactory.trigger_event(
            event,
            self.config,
            **default_kw,
        )

        assert received_extra_kwargs == default_kw

    @pytest.mark.asyncio
    async def test_trigger_event_no_handlers(self):
        """Test trigger_event when no handlers are registered."""
        event = TestEvent()
        # Should not raise any exception
        await MatcherFactory.trigger_event(event, self.config)

    @pytest.mark.asyncio
    async def test_trigger_event_with_exception_ignored(self):
        """Test trigger_event with exception_ignored parameter."""

        matcher = Matcher("test_event", block=False)  # Set block=False

        @matcher.handle()
        async def test_handler(event: TestEvent, config: AmritaConfig):
            raise SpecException()

        event = TestEvent()
        with pytest.raises(SpecException):
            await MatcherFactory.trigger_event(
                event, self.config, exception_ignored=(SpecException,)
            )


class TestEventRegistry:
    """Test EventRegistry singleton."""

    def setup_method(self):
        """Clear registry before test."""
        EventRegistry()._event_handlers.clear()

    def teardown_method(self):
        """Clear registry after test."""
        EventRegistry()._event_handlers.clear()

    def test_singleton_pattern(self):
        """Test that EventRegistry follows singleton pattern."""
        registry1 = EventRegistry()
        registry2 = EventRegistry()
        assert registry1 is registry2

    def test_get_handlers_nonexistent(self):
        """Test getting handlers for non-existent event type."""
        registry = EventRegistry()
        handlers = registry.get_handlers("nonexistent_event")
        assert handlers == {}


# Integration tests for complete workflow
class TestMatcherIntegration:
    """Integration tests for complete matcher workflow."""

    def setup_method(self):
        """Setup test environment."""
        self.config = AmritaConfig()
        EventRegistry()._event_handlers.clear()

    def teardown_method(self):
        """Cleanup after test."""
        EventRegistry()._event_handlers.clear()

    @pytest.mark.asyncio
    async def test_complete_dependency_injection_workflow(self):
        """Test complete workflow with both runtime and default dependencies."""
        results = {}

        async def runtime_dep() -> str:
            return "runtime_value"

        async def default_dep() -> str:
            return "default_value"

        matcher = Matcher("test_event", block=False)  # Set block=False

        @matcher.handle()
        async def test_handler(
            event: TestEvent,
            config: AmritaConfig,
            runtime_param: str,
            default_param: str = Depends(default_dep),
        ):
            results["runtime_param"] = runtime_param
            results["default_param"] = default_param

        event = TestEvent()
        await MatcherFactory.trigger_event(
            event, self.config, **{"runtime_param": Depends(runtime_dep)}
        )

        assert results["runtime_param"] == "runtime_value"
        assert results["default_param"] == "default_value"

    @pytest.mark.asyncio
    async def test_concurrent_dependency_resolution(self):
        """Test that dependencies are resolved concurrently."""
        resolution_order = []

        async def slow_dep(name: str) -> str:
            await asyncio.sleep(0.01)  # Small delay to test concurrency
            resolution_order.append(name)
            return f"value_{name}"

        matcher = Matcher("test_event", block=False)  # Set block=False

        @matcher.handle()
        async def test_handler(
            event: TestEvent, config: AmritaConfig, dep1: str, dep2: str, dep3: str
        ):
            pass

        event = TestEvent()
        await MatcherFactory.trigger_event(
            event,
            self.config,
            **{
                "dep1": Depends(lambda: slow_dep("dep1")),
                "dep2": Depends(lambda: slow_dep("dep2")),
                "dep3": Depends(lambda: slow_dep("dep3")),
            },
        )

        # All dependencies should be resolved, but order may vary due to concurrency
        assert len(resolution_order) == 3
        assert set(resolution_order) == {"dep1", "dep2", "dep3"}
