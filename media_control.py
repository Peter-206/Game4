"""Best-effort Windows media-session pause/resume for song events."""

from __future__ import annotations

import asyncio
import threading


class WindowsMediaPauser:
    """Pause playing GSMTC sessions and resume only the sessions we paused."""

    def __init__(self):
        self._paused_sessions = []
        self._lock = threading.Lock()
        try:
            from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
            self.available = GlobalSystemMediaTransportControlsSessionManager is not None
        except (ImportError, OSError):
            self.available = False

    @staticmethod
    async def _playing_sessions():
        try:
            from winrt.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as SessionManager,
                GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
            )
        except (ImportError, OSError):
            return []
        manager = await SessionManager.request_async()
        return [session for session in manager.get_sessions()
                if session.get_playback_info().playback_status == PlaybackStatus.PLAYING]

    async def _pause(self):
        paused = []
        for session in await self._playing_sessions():
            try:
                if await session.try_pause_async():
                    paused.append(session)
            except (OSError, RuntimeError):
                continue
        with self._lock:
            self._paused_sessions = paused

    async def _resume(self):
        with self._lock:
            sessions, self._paused_sessions = self._paused_sessions, []
        for session in sessions:
            try:
                await session.try_play_async()
            except (OSError, RuntimeError):
                continue

    @staticmethod
    def _run_safely(operation):
        try:
            asyncio.run(operation())
        except Exception:
            # Media-session access is optional and must never block the game.
            return

    def pause_async(self):
        threading.Thread(target=lambda: self._run_safely(self._pause),
                         name="pause-host-media", daemon=True).start()

    def resume_async(self):
        threading.Thread(target=lambda: self._run_safely(self._resume),
                         name="resume-host-media", daemon=True).start()
