#    Friendly Telegram (telegram userbot)
#    Copyright (C) 2018-2019 The Authors

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

from .. import loader, utils, security
import logging

from telethon.tl.types import ChatAdminRights, ChatBannedRights, PeerUser, PeerChannel
from telethon.errors import BadRequestError
from telethon.tl.functions.channels import EditAdminRequest, EditBannedRequest
from telethon.tl.functions.messages import EditChatAdminRequest

logger = logging.getLogger(__name__)


@loader.tds
class BanMod(loader.Module):
    """Group administration tasks"""
    strings = {"name": "LINUXILadmintool",
               "ban_not_supergroup": "<b>I can't ban someone unless they're in a supergroup!</b>",
               "unban_not_supergroup": "<b>I can't unban someone unless they're banned from a supergroup!</b>",
               "kick_not_group": "<b>I can't kick someone unless they're in a group!</b>",
               "mute_not_supergroup": "<b>I can't mute someone unless they're in a supergroup!</b>",
               "unmute_not_supergroup": "<b>I can't un-mute someone unless they're in a supergroup!</b>",
               "ban_none": "<b>I can't ban no-one, can I?</b>",
               "unban_none": "<b>I need someone to unbanned here.</b>",
               "kick_none": "<b>I need someone to be kicked out of the chat.</b>",
               "promote_none": "<b>I can't promote no one, can I?</b>",
               "demote_none": "<b>I can't demote no one, can I?</b>",
               "mute_none": "<b>I can't mute no-one, can I?</b>",
               "unmute_none": "<b>I can't unmute no-one, can I?</b>",
               "who": "<b>Who the hell is that?</b>",
               "not_admin": "<b>Am I an admin here?</b>",
               "banned": "<b>Banned</b> <code>{}</code> <b>from the chat!</b>",
               "unbanned": "<b>Unbanned</b> <code>{}</code> <b>from the chat!</b>",
               "kicked": "<b>Kicked</b> <code>{}</code> <b>from the chat!</b>",
               "promoted": "<code>{}</code> <b>is now powered with admin rights!</b>",
               "demoted": "<code>{}</code> <b>is now stripped off of their admin rights!</b>",
               "muted": "<b>Muted</b> <code>{}</code> <b>in the chat!</b>",
               "unmuted": "<b>Unmuted</b> <code>{}</code> <b>in the chat!</b>"}

    @loader.group_admin_ban_users
    @loader.ratelimit
    async def bancmd(self, message):
        """Ban the user from the group"""
        if not isinstance(message.to_id, PeerChannel):
            return await utils.answer(message, self.strings("ban_not_supergroup", message))
        if message.is_reply:
            user = await utils.get_user(await message.get_reply_message())
        else:
            args = utils.get_args(message)
            if not args:
                return await utils.answer(message, self.strings("ban_none", message))
            user = await self.client.get_entity(int_or_str(args[0]))
        if not user:
            return await utils.answer(message, self.strings("who", message))
        logger.debug(user)
        try:
            await self.client(EditBannedRequest(message.chat_id, user.id,
                                                ChatBannedRights(until_date=None, view_messages=True)))
        except BadRequestError:
            await utils.answer(message, self.strings("not_admin", message))
        else:
            await self.allmodules.log("ban", group=message.chat_id, affected_uids=[user.id])
            await utils.answer(message,
                               self.strings("banned", message).format(utils.escape_html(ascii(user.first_name))))

    @loader.group_admin_ban_users
    @loader.ratelimit
    async def unbancmd(self, message):
        """Lift the ban off the user."""
        if not isinstance(message.to_id, PeerChannel):
            return await utils.answer(message, self.strings("not_supergroup", message))
        if message.is_reply:
            user = await utils.get_user(await message.get_reply_message())
        else:
            args = utils.get_args(message)
            if not args:
                return await utils.answer(message, self.strings("unban_none", message))
            user = await self.client.get_entity(int_or_str(args[0]))
        if not user:
            return await utils.answer(message, self.strings("who", message))
        logger.debug(user)
        try:
            await self.client(EditBannedRequest(message.chat_id, user.id,
                              ChatBannedRights(until_date=None, view_messages=False)))
        except BadRequestError:
            await utils.answer(message, self.strings("not_admin", message))
        else:
            await self.allmodules.log("unban", group=message.chat_id, affected_uids=[user.id])
            await utils.answer(message,
                               self.strings("unbanned", message).format(utils.escape_html(ascii(user.first_name))))

    @loader.group_admin_ban_users
    @loader.ratelimit
    async def kickcmd(self, message):
        """Kick the user out of the group"""
        if isinstance(message.to_id, PeerUser):
            return await utils.answer(message, self.strings("not_group", message))
        if message.is_reply:
            user = await utils.get_user(await message.get_reply_message())
        else:
            args = utils.get_args(message)
            if not args:
                return await utils.answer(message, self.strings("kick_none", message))
            user = await self.client.get_entity(int_or_str(args[0]))
        if not user:
            return await utils.answer(message, self.strings("who", message))
        logger.debug(user)
        if user.is_self:
            if not (await message.client.is_bot()
                    or await self.allmodules.check_security(message, security.OWNER | security.SUDO)):
                return
        try:
            await self.client.kick_participant(message.chat_id, user.id)
        except BadRequestError:
            await utils.answer(message, self.strings("not_admin", message))
        else:
            await self.allmodules.log("kick", group=message.chat_id, affected_uids=[user.id])
            await utils.answer(message,
                               self.strings("kicked", message).format(utils.escape_html(ascii(user.first_name))))

    @loader.group_admin_add_admins
    @loader.ratelimit
    async def promotecmd(self, message):
        """Provides admin rights to the specified user."""
        if message.is_reply:
            user = await utils.get_user(await message.get_reply_message())
        else:
            args = utils.get_args(message)
            if not args:
                return await utils.answer(message, self.strings("promote_none", message))
            user = await self.client.get_entity(int_or_str(args[0]))
        if not user:
            return await utils.answer(message, self.strings("who", message))
        rank = ""
        if args:
            rank = args[1]
        logger.debug(user)
        try:
            if message.is_channel:
                await self.client(EditAdminRequest(message.chat_id, user.id,
                                                   ChatAdminRights(post_messages=None,
                                                                   add_admins=None,
                                                                   invite_users=None,
                                                                   change_info=None,
                                                                   ban_users=None,
                                                                   delete_messages=True,
                                                                   pin_messages=True,
                                                                   edit_messages=None), rank))
        except BadRequestError:
            await utils.answer(message, self.strings("not_admin", message))
        else:
            await self.allmodules.log("promote", group=message.chat_id, affected_uids=[user.id])
            await utils.answer(message,
                               self.strings("promoted", message).format(utils.escape_html(ascii(user.first_name))))

    @loader.group_admin_add_admins
    async def demotecmd(self, message):
        """Removes admin rights of the specified group admin."""
        if message.is_reply:
            user = await utils.get_user(await message.get_reply_message())
        else:
            args = utils.get_args(message)
            if not args:
                return await utils.answer(message, self.strings("demote_none", message))
            user = await self.client.get_entity(int_or_str(args[0]))
        if not user:
            return await utils.answer(message, self.strings("who", message))
        logger.debug(user)
        try:
            if message.is_channel:
                await self.client(EditAdminRequest(message.chat_id, user.id,
                                                   ChatAdminRights(post_messages=None,
                                                                   add_admins=None,
                                                                   invite_users=None,
                                                                   change_info=None,
                                                                   ban_users=None,
                                                                   delete_messages=None,
                                                                   pin_messages=None,
                                                                   edit_messages=None), ""))
            else:
                await self.client(EditChatAdminRequest(message.chat_id, user.id, False))
        except BadRequestError:
            await utils.answer(message, self.strings("not_admin", message))
        else:
            await self.allmodules.log("demote", group=message.chat_id, affected_uids=[user.id])
            await utils.answer(message,
                               self.strings("demoted", message).format(utils.escape_html(ascii(user.first_name))))

    async def mutecmd(self, message):
        """Mutes the user in the group"""
        if not isinstance(message.to_id, PeerChannel):
            return await utils.answer(message, self.strings("mute_not_supergroup", message))
        if message.is_reply:
            user = await utils.get_user(await message.get_reply_message())
        else:
            args = utils.get_args(message)
            if not args:
                return await utils.answer(message, self.strings("mute_none", message))
            user = await self.client.get_entity(int_or_str(args[0]))
        if not user:
            return await utils.answer(message, self.strings("who", message))
        logger.debug(user)
        try:
            await self.client(EditBannedRequest(message.chat_id, user.id,
                                                ChatBannedRights(until_date=None, send_messages=True)))
        except BadRequestError:
            await utils.answer(message, self.strings("not_admin", message))
        else:
            await self.allmodules.log("mute", group=message.chat_id, affected_uids=[user.id])
            await utils.answer(message, self.strings("muted",
                                                     message).format(utils.escape_html(ascii(user.first_name))))

    async def unmutecmd(self, message):
        """Unmutes the user in the group"""
        if not isinstance(message.to_id, PeerChannel):
            return await utils.answer(message, self.strings("unmute_not_supergroup", message))
        if message.is_reply:
            user = await utils.get_user(await message.get_reply_message())
        else:
            args = utils.get_args(message)
            if not args:
                return await utils.answer(message, self.strings("unmute_none", message))
            user = await self.client.get_entity(int_or_str(args[0]))
        if not user:
            return await utils.answer(message, self.strings("who", message))
        logger.debug(user)
        try:
            await self.client(EditBannedRequest(message.chat_id, user.id, ChatBannedRights(until_date=None,
                                                view_messages=None, send_messages=False, send_media=False,
                                                send_stickers=False, send_gifs=False, send_games=False,
                                                send_inline=False, embed_links=False)))
        except BadRequestError:
            await utils.answer(message, self.strings("not_admin", message))
        else:
            await self.allmodules.log("unmute", group=message.chat_id, affected_uids=[user.id])
            await utils.answer(message, self.strings("unmuted",
                                                     message).format(utils.escape_html(ascii(user.first_name))))

    async def client_ready(self, client, db):
        self.client = client


def int_or_str(arg):
    try:
        return int(arg)
    except ValueError:
        return arg
