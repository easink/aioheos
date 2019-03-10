#!/usr/bin/env python3
" Heos Player "

from pytz import UTC
from datetime import datetime

import logging

_LOGGER = logging.getLogger(__name__)


class AioHeosPlayer():
    " Asynchronous Heos Player class "

    def __init__(self, controller, player_json):
        self._player_info = player_json
        self._player_id = str(player_json['pid'])
        self._controller = controller
        self._sid = None
        self._source_name = None
        self._qid = None
        self._online = False
        self._play_state = None
        self._mute_state = None
        self._volume_level = 0
        self._current_position = 0
        self._current_position_updated_at = None
        self._duration = 0
        self._media_artist = None
        self._media_album = None
        self._media_title = None
        self._media_image_url = None
        self._media_id = None
        self._callback = None
        _LOGGER.debug("[D] Creating player object %s for controller pid %s",
                      self._player_id, self._controller._player_id)

    @property
    def state_change_callback(self):
        " get state_change_callback "
        return self._callback

    @state_change_callback.setter
    def state_change_callback(self, callback):
        self._callback = callback

    @property
    def player_id(self):
        " get player id "
        return self._player_id

    @property
    def name(self):
        " get player name "
        return self._player_info['name']

    @property
    def ip_address(self):
        " get player name "
        return self._player_info['ip']

    @property
    def volume(self):
        " get volume "
        return self._volume_level

    @volume.setter
    def volume(self, value):
        self._volume_level = value
        self._online = True
        self.notify_listeners()

    @property
    def current_position_updated_at(self):
        " get current_position_updated_at "
        return self._current_position_updated_at

    @property
    def duration(self):
        " get dureation "
        return self._duration

    @duration.setter
    def duration(self, duration):
        self._duration = duration
        self.notify_listeners()

    @property
    def current_position(self):
        " get current_position "
        return self._current_position

    @current_position.setter
    def current_position(self, current_position):
        self._current_position = current_position
        self._current_position_updated_at = datetime.now(UTC)
        self.notify_listeners()

    @property
    def mute(self):
        " get mute "
        return self._mute_state

    @mute.setter
    def mute(self, value):
        self._mute_state = value
        self.notify_listeners()

    @property
    def play_state(self):
        " get play state "
        return self._play_state

    @play_state.setter
    def play_state(self, value):
        self._play_state = value
        self._online = bool(value)
        self.notify_listeners()

    @property
    def media_artist(self):
        " get media artist "
        return self._media_artist

    @media_artist.setter
    def media_artist(self, value):
        self._media_artist = value
        self.notify_listeners()

    @property
    def media_album(self):
        " get media album "
        return self._media_album

    @media_album.setter
    def media_album(self, value):
        self._media_album = value
        self.notify_listeners()

    @property
    def media_title(self):
        " get media title "
        return self._media_title

    @media_title.setter
    def media_title(self, value):
        self._media_title = value
        self.notify_listeners()

    @property
    def media_image_url(self):
        " get media image url "
        return self._media_image_url

    @media_image_url.setter
    def media_image_url(self, value):
        self._media_image_url = value
        self.notify_listeners()

    @property
    def media_id(self):
        " get media_id "
        return self._media_id

    @media_id.setter
    def media_id(self, value):
        self._media_id = value

    @property
    def online(self):
        """Return True if entity is available."""
        return self._online

    @property
    def player_info(self):
        """Player info"""
        return self._player_info

    @player_info.setter
    def player_info(self, info):
        self._player_info = info
        self.notify_listeners()

    def toggle_mute(self):
        " toggle mute "
        self._controller.toggle_mute(self.player_id)

    def set_mute(self, mute):
        " set mute "
        self._controller.toggle_mute(self.player_id, mute)

    def reset_now_playing(self):
        """Reset now playing"""
        self._media_artist = None
        self._media_album = None
        self._media_title = None
        self._media_image_url = None
        self._media_id = None

    def request_update(self):
        """Request update"""
        self._controller.request_play_state(self.player_id)
        self._controller.request_mute_state(self.player_id)
        self._controller.request_volume(self.player_id)
        self._controller.request_now_playing_media(self.player_id)

    def volume_level_up(self, step=10):
        " volume level up "
        self.set_volume(self._volume_level + step)

    def volume_level_down(self, step=10):
        " volume level down "
        self.set_volume(self._volume_level - step)

    def stop(self):
        " stop player "
        self._controller.stop(self.player_id)

    def play(self):
        " play "
        self._controller.play(self.player_id)

    def pause(self):
        " pause "
        self._controller.pause(self.player_id)

    def play_next(self):
        " next "
        self._controller.request_play_next(self.player_id)

    def play_prev(self):
        " prev "
        self._controller.request_play_previous(self.player_id)

    def play_favorite(self, fav_mid):
        " Favorites "
        self._controller.play_favourite(self.player_id, fav_mid)

    def play_stream(self, sid, mid):
        " Favorites "
        self._controller.play_stream(self.player_id, sid, mid)

    def play_source(self, source):
        " Sourced "
        for src in self._controller._music_sources:
            if src['name'] == source:
                self._controller.play_stream(self.player_id, src['sid'], None)

    def set_volume(self, volume):
        """Set volume"""
        self._controller.set_volume(volume, self.player_id)

    def source_list(self):
        """Source list"""
        return self._controller.get_music_sources()

    def favourites_list(self):
        """Favourites list"""
        return self._controller.get_favourites()

    def create_group(self, devices):
        """Create group"""
        slave_ids = [slave for slave in devices if slave != self.player_id]
        self._controller.set_group(self.player_id, slave_ids)

    @property
    def sid(self):
        """Sid"""
        return self._sid

    @sid.setter
    def sid(self, value):
        self._sid = value

    @property
    def source_name(self):
        """Source name"""
        return self._source_name

    @source_name.setter
    def source_name(self, value):
        self._source_name = value

    @property
    def qid(self):
        """Qid"""
        return self._qid

    @qid.setter
    def qid(self, value):
        self._qid = value

    def notify_listeners(self):
        """Notify listeners"""
        if self._callback:
            self._callback()
