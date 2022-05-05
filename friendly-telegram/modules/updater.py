
import atexit
import functools
import logging
import os
import subprocess
import sys
import asyncio
from typing import Union

import git
from git import Repo, GitCommandError
from telethon.tl.types import Message

from .. import loader, utils
from ..inline.types import InlineCall

logger = logging.getLogger(__name__)


@loader.tds
class UpdaterMod(loader.Module):
    """Updates itself"""


    strings = {
        "source": "ℹ️ <b>Исходный код можно прочитать</b> <a href='{}'>здесь</a>",
        "restarting_caption": "🔄 <b>Перезагрузка...</b>",
        "downloading": "🔄 <b>Скачивание обновлений...</b>",
        "downloaded": "✅ <b>Скачано успешно.\nНапиши</b> \n<code>.restart</code> <b>для перезагрузки юзербота.</b>",
        "installing": "🔁 <b>Установка обновлений...</b>",
        "success": "✅ <b>Перезагрузка успешна!</b>",
        "origin_cfg_doc": "Ссылка, из которой будут загружаться обновления",
        "btn_restart": "🔄 Перезагрузиться",
        "btn_update": "⛵️ Обновиться",
        "restart_confirm": "🔄 <b>Ты уверен, что хочешь перезагрузиться?</b>",
        "update_confirm": "⛵️ <b>Ты уверен, что хочешь обновиться?</b>",
        "cancel": "🚫 Отмена",
        "_cmd_doc_restart": "Перезагружает юзербот",
        "_cmd_doc_download": "Скачивает обновления",
        "_cmd_doc_update": "Обновляет юзербот",
        "_cmd_doc_source": "Ссылка на исходный код проекта",
        "_cls_doc": "Обновляет юзербот",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "GIT_ORIGIN_URL",
            "https://github.com/AmoreForever/linux",
            lambda: self.strings("origin_cfg_doc"),
        )

    @loader.owner
    async def restartcmd(self, message: Message):
        """Restarts the userbot"""
        try:
            if (
                "--force" in (utils.get_args_raw(message) or "")
                or not self.inline.init_complete
                or not await self.inline.form(
                    message=message,
                    text=self.strings("restart_confirm"),
                    reply_markup=[
                        {
                            "text": self.strings("btn_restart"),
                            "callback": self.inline_restart,
                        },
                        {"text": self.strings("cancel"), "callback": self.inline_close},
                    ],
                )
            ):
                raise
        except Exception:
            message = await utils.answer(message, self.strings("restarting_caption"))

            await self.restart_common(message)

    async def inline_restart(self, call: InlineCall):
        await call.edit(self.strings("restarting_caption"))
        await self.restart_common(call)

    async def inline_close(self, call: InlineCall):
        await call.delete()

    async def prerestart_common(self, call: Union[InlineCall, Message]):
        logger.debug(f"Self-update. {sys.executable} -m {utils.get_base_dir()}")
        if hasattr(call, "inline_message_id"):
            self._db.set(__name__, "selfupdatemsg", call.inline_message_id)
        else:
            self._db.set(
                __name__, "selfupdatemsg", f"{utils.get_chat_id(call)}:{call.id}"
            )

    async def restart_common(self, call: Union[InlineCall, Message]):
        if (
            hasattr(call, "form")
            and isinstance(call.form, dict)
            and "uid" in call.form
            and call.form["uid"] in self.inline._forms
            and "message" in self.inline._forms[call.form["uid"]]
        ):
            message = self.inline._forms[call.form["uid"]]["message"]
        else:
            message = call

        await self.prerestart_common(call)
        atexit.register(functools.partial(restart, *sys.argv[1:]))
        handler = logging.getLogger().handlers[0]
        handler.setLevel(logging.CRITICAL)
        for client in self.allclients:
            # Terminate main loop of all running clients
            # Won't work if not all clients are ready
            if client is not message.client:
                await client.disconnect()

        await message.client.disconnect()

    async def download_common(self):
        try:
            repo = Repo(os.path.dirname(utils.get_base_dir()))
            origin = repo.remote("origin")
            r = origin.pull()
            new_commit = repo.head.commit
            for info in r:
                if info.old_commit:
                    for d in new_commit.diff(info.old_commit):
                        if d.b_path == "requirements.txt":
                            return True
            return False
        except git.exc.InvalidGitRepositoryError:
            repo = Repo.init(os.path.dirname(utils.get_base_dir()))
            origin = repo.create_remote("origin", self.config["GIT_ORIGIN_URL"])
            origin.fetch()
            repo.create_head("master", origin.refs.master)
            repo.heads.master.set_tracking_branch(origin.refs.master)
            repo.heads.master.checkout(True)
            return False

    @staticmethod
    def req_common():
        # Now we have downloaded new code, install requirements
        logger.debug("Installing new requirements...")
        try:
            subprocess.run(  # skipcq: PYL-W1510
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    os.path.join(
                        os.path.dirname(utils.get_base_dir()), "requirements.txt"
                    ),
                    "--user",
                ]
            )

        except subprocess.CalledProcessError:
            logger.exception("Req install failed")

    @loader.owner
    async def updatecmd(self, message: Message):
        """Downloads userbot updates"""
        try:
            if (
                "--force" in (utils.get_args_raw(message) or "")
                or not self.inline.init_complete
                or not await self.inline.form(
                    message=message,
                    text=self.strings("update_confirm"),
                    reply_markup=[
                        {
                            "text": self.strings("btn_update"),
                            "callback": self.inline_update,
                        },
                        {"text": self.strings("cancel"), "callback": self.inline_close},
                    ],
                )
            ):
                raise
        except Exception:
            await self.inline_update(message)

    async def inline_update(
        self,
        call: Union[InlineCall, Message],
        hard: bool = False,
    ):
        # We don't really care about asyncio at this point, as we are shutting down
        if hard:
            os.system(f"cd {utils.get_base_dir()} && cd .. && git reset --hard HEAD")  # fmt: skip

        try:
            try:
                await utils.answer(call, self.strings("downloading"))
            except Exception:
                pass

            req_update = await self.download_common()

            try:
                await utils.answer(call, self.strings("installing"))
            except Exception:
                pass

            if req_update:
                self.req_common()

            try:
                await utils.answer(call, self.strings("restarting_caption"))
            except Exception:
                pass

            await self.restart_common(call)
        except GitCommandError:
            if not hard:
                await self.inline_update(call, True)
                return

            logger.critical("Got update loop. Update manually via .terminal")
            return

    @loader.unrestricted
    async def sourcecmd(self, message: Message):
        """Links the source code of this project"""
        await utils.answer(
            message,
            self.strings("source").format(self.config["GIT_ORIGIN_URL"]),
        )

    async def client_ready(self, client, db):
        self._db = db
        self._me = await client.get_me()
        self._client = client

        if db.get(__name__, "selfupdatemsg") is not None:
            try:
                await self.update_complete(client)
            except Exception:
                logger.exception("Failed to complete update!")

        self._db.set(__name__, "selfupdatemsg", None)

    async def update_complete(self, client):
        logger.debug("Self update successful! Edit message")
        msg = self.strings("success")
        ms = self._db.get(__name__, "selfupdatemsg")

        if ":" in str(ms):
            chat_id, message_id = ms.split(":")
            chat_id, message_id = int(chat_id), int(message_id)
            await self._client.edit_message(chat_id, message_id, msg)
            await asyncio.sleep(120)
            await self._client.delete_messages(chat_id, message_id)
            return

        await self.inline.bot.edit_message_text(
            inline_message_id=ms,
            text=msg,
            parse_mode="HTML",
        )


def restart(*argv):
    os.execl(
        sys.executable,
        sys.executable,
        "-m",
        os.path.relpath(utils.get_base_dir()),
        *argv,
    )
