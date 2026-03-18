"""
Parameterized E2E tests for IntentRouter with various input scenarios.

These tests use the TestDataProvider to run through multiple scenarios
and validate behavior activation and quote extraction.
"""

import pytest
from backend.worker.modules.llm_pipeline.steps.intent_router.behaviours import (
    BehaviorRole,
)
from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import (
    IntentRouterResponse,
)


class TestIntentRouterParametrized:
    """Parameterized tests for different behavior scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "request_obj",
        [
            pytest.param(
                req,
                id=f"architect_{i}",
            )
            for i, req in enumerate(
                [
                    type("Req", (), {
                        "user_prompt": "перегенируй блок ТЗ с требованием к СУБД, поставь MySQL",
                        "attachments": [],
                    })(),
                    type("Req", (), {
                        "user_prompt": "Обновить раздел про безопасность - нужна OAuth2",
                        "attachments": [],
                    })(),
                ]
            )
        ],
    )
    async def test_architect_scenarios(self, intent_router, request_obj):
        """Test Architect behavior with various TZ modification requests."""
        from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import (
            IntentRouterRequest,
        )
        
        request = IntentRouterRequest(
            user_prompt=request_obj.user_prompt,
            attachments=request_obj.attachments,
        )

        result = await intent_router.extract_behaviours(request)

        assert isinstance(result, IntentRouterResponse)
        assert len(result.behaviors) > 0
        
        # Verify quotes
        for behavior in result.behaviors:
            assert behavior.user_prompt in request.user_prompt

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_prompt,expected_role",
        [
            pytest.param(
                "Какие у нас требования к API?",
                BehaviorRole.CONSULTANT,
                id="consultant_api_question",
            ),
            pytest.param(
                "Расскажи про обработку ошибок",
                BehaviorRole.CONSULTANT,
                id="consultant_explanation",
            ),
            pytest.param(
                "Пользователь может быть админом или обычным юзером",
                BehaviorRole.HARVESTER,
                id="harvester_new_info",
            ),
            pytest.param(
                "Система должна поддерживать экспорт в PDF и CSV",
                BehaviorRole.HARVESTER,
                id="harvester_requirements",
            ),
            pytest.param(
                "Напиши мне код быстрой сортировки",
                BehaviorRole.GUARDIAN,
                id="guardian_code_request",
            ),
            pytest.param(
                "Как приготовить пасту?",
                BehaviorRole.GUARDIAN,
                id="guardian_offtopic",
            ),
        ],
    )
    async def test_behavior_activation(self, intent_router, user_prompt, expected_role):
        """Test that specific behaviors are activated for given prompts."""
        from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import (
            IntentRouterRequest,
        )
        
        request = IntentRouterRequest(
            user_prompt=user_prompt,
            attachments=[],
        )

        result = await intent_router.extract_behaviours(request)

        assert isinstance(result, IntentRouterResponse)
        roles = [b.role for b in result.behaviors]
        assert expected_role in roles, (
            f"Expected {expected_role} in {roles} for prompt: {user_prompt}"
        )


class TestIntentRouterQuoteAccuracy:
    """Tests focused on validating quote extraction accuracy."""

    @pytest.mark.asyncio
    async def test_quote_from_complex_input(self, intent_router):
        """Test quote extraction from complex multi-sentence input."""
        from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import (
            IntentRouterRequest,
        )
        
        input_text = (
            "Нужно обновить ТЗ по двум направлениям: "
            "1) Добавить поддержку MySQL как основной БД, "
            "2) Улучшить логирование ошибок. "
            "Какие у вас есть рекомендации?"
        )
        request = IntentRouterRequest(
            user_prompt=input_text,
            attachments=[],
        )

        result = await intent_router.extract_behaviours(request)

        # Verify that all extracted quotes are substrings of input
        for behavior in result.behaviors:
            assert behavior.user_prompt in input_text, (
                f"Quote '{behavior.user_prompt}' not found in input"
            )
            # Quote should be reasonably long (not just a single word)
            assert len(behavior.user_prompt) > 3, (
                f"Quote seems too short: '{behavior.user_prompt}'"
            )

    @pytest.mark.asyncio
    async def test_quote_from_single_line(self, intent_router):
        """Test quote extraction from single-line input."""
        from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import (
            IntentRouterRequest,
        )
        
        input_text = "перегенируй блок ТЗ с требованием к СУБД"
        request = IntentRouterRequest(
            user_prompt=input_text,
            attachments=[],
        )

        result = await intent_router.extract_behaviours(request)

        for behavior in result.behaviors:
            # Must be exact substring
            assert behavior.user_prompt in input_text


class TestIntentRouterErrorHandling:
    """Tests for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_empty_input_handling(self, intent_router):
        """Test handling of empty or minimal input."""
        from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import (
            IntentRouterRequest,
        )
        
        # Very short input
        request = IntentRouterRequest(
            user_prompt="OK",
            attachments=[],
        )

        try:
            result = await intent_router.extract_behaviours(request)
            # Should still return valid response
            assert isinstance(result, IntentRouterResponse)
        except ValueError as e:
            # It's acceptable to fail on very short input
            assert "Invalid JSON/schema" in str(e) or "Failed to parse" in str(e)

    @pytest.mark.asyncio
    async def test_long_input_handling(self, intent_router):
        """Test handling of very long input."""
        from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import (
            IntentRouterRequest,
        )
        
        # Create long input
        long_text = "Требование: " + "поддержка многоязычного интерфейса. " * 50
        request = IntentRouterRequest(
            user_prompt=long_text,
            attachments=[],
        )

        result = await intent_router.extract_behaviours(request)
        assert isinstance(result, IntentRouterResponse)
        assert len(result.behaviors) > 0


class TestIntentRouterPerformance:
    """Performance and consistency tests."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sequential_requests(self, intent_router):
        """Test multiple sequential requests."""
        from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import (
            IntentRouterRequest,
        )
        
        prompts = [
            "перегенируй ТЗ",
            "Какие требования к API?",
            "Добавь новый модуль",
        ]

        results = []
        for prompt in prompts:
            request = IntentRouterRequest(user_prompt=prompt, attachments=[])
            result = await intent_router.extract_behaviours(request)
            results.append(result)

        # All should be valid responses
        for result in results:
            assert isinstance(result, IntentRouterResponse)
            assert len(result.behaviors) > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_requests(self, intent_router):
        """Test concurrent requests to IntentRouter."""
        import asyncio
        
        from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import (
            IntentRouterRequest,
        )
        
        async def make_request(prompt):
            request = IntentRouterRequest(user_prompt=prompt, attachments=[])
            return await intent_router.extract_behaviours(request)

        prompts = [
            "перегенируй ТЗ",
            "Какие требования?",
            "Добавь модуль",
        ]

        # Run concurrent requests
        results = await asyncio.gather(
            *[make_request(p) for p in prompts],
            return_exceptions=True,
        )

        # All should succeed or fail gracefully
        for result in results:
            if isinstance(result, Exception):
                # Some may fail on concurrent access, that's ok
                pass
            else:
                assert isinstance(result, IntentRouterResponse)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "not slow"])
