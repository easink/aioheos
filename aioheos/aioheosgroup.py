#!/usr/bin/env python3
" Heos Group "

import logging
from . import aioheosplayer

_LOGGER = logging.getLogger(__name__)


class AioHeosGroup(aioheosplayer.AioHeosPlayer):
    " Asynchronous Heos Group class "

    def __init__(self, controller, group_json):
        group_json["pid"] = group_json["gid"]
        super().__init__(controller, group_json)
        _LOGGER.debug("[D] Creating group object %s for controller pid %s",
                      self._player_id, self._controller._player_id)

    def recreate_group(self):
        " Recreate group "
        member_ids = []
        for player in self._player_info["players"]:
            if str(player["pid"]) != str(self.player_id):
                member_ids.append(player["pid"])
        self._controller.set_group(self.player_id, member_ids)
