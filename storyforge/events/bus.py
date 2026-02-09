"""Async event bus for inter-agent communication."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable, Optional

from storyforge.events.types import Event, EventType

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], Awaitable[Optional[Event]]]
Middleware = Callable[[Event], Awaitable[Optional[Event]]]


class EventBus:
    """Async pub/sub event bus with request-response support."""

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._directed_handlers: dict[str, EventHandler] = {}
        self._event_log: list[Event] = []
        self._middleware: list[Middleware] = []
        self._response_futures: dict[str, asyncio.Future[Event]] = {}

    async def subscribe(
        self, event_type: EventType, handler: EventHandler
    ) -> None:
        """Register a handler for a specific event type."""
        self._subscribers[event_type].append(handler)

    async def subscribe_directed(
        self, agent_name: str, handler: EventHandler
    ) -> None:
        """Register a handler for events directed at a specific agent."""
        self._directed_handlers[agent_name] = handler

    async def publish(self, event: Event) -> None:
        """Publish an event to all matching subscribers."""
        # Run middleware chain
        processed: Optional[Event] = event
        for mw in self._middleware:
            processed = await mw(processed)
            if processed is None:
                return
        event = processed

        self._event_log.append(event)

        # Check if this event resolves a pending future
        if (
            event.correlation_id
            and event.correlation_id in self._response_futures
        ):
            future = self._response_futures[event.correlation_id]
            if not future.done():
                future.set_result(event)
            return

        # Directed event — send only to the target agent
        if event.target_agent and event.target_agent in self._directed_handlers:
            try:
                response = await self._directed_handlers[event.target_agent](
                    event
                )
                if response is not None:
                    await self.publish(response)
            except Exception:
                logger.exception(
                    "Handler error for directed event to %s",
                    event.target_agent,
                )
            return

        # Broadcast to all subscribers of this event type
        handlers = self._subscribers.get(event.event_type, [])
        tasks = [handler(event) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Event):
                await self.publish(result)
            elif isinstance(result, Exception):
                logger.exception(
                    "Handler error for %s: %s", event.event_type, result
                )

    async def request(
        self, event: Event, timeout: float = 60.0
    ) -> Event:
        """Publish an event and wait for a correlated response."""
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Event] = loop.create_future()
        self._response_futures[event.event_id] = future

        await self.publish(event)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"No response for event {event.event_id} "
                f"({event.event_type.value}) within {timeout}s"
            )
        finally:
            self._response_futures.pop(event.event_id, None)

    def add_middleware(self, middleware: Middleware) -> None:
        """Add a middleware function to the processing chain."""
        self._middleware.append(middleware)

    def get_event_log(
        self,
        event_type: Optional[EventType] = None,
        chapter: Optional[int] = None,
    ) -> list[Event]:
        """Retrieve logged events, optionally filtered."""
        events = self._event_log
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        if chapter is not None:
            events = [e for e in events if e.chapter_number == chapter]
        return events

    def clear_log(self) -> None:
        """Clear the event log."""
        self._event_log.clear()
