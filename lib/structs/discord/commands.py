"""
Custom Discord command interface implementation for GitBot
~~~~~~~~~~~~~~~~~~~
A set of non-native replacements for command objects provided in discord.ext.commands
:copyright: (c) 2020-present statch
:license: CC BY-NC-ND 4.0, see LICENSE for more details.
"""

from discord.ext import commands
from typing import Callable, Generator, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from lib.structs.discord.context import GitBotContext
from lib.typehints import ArgumentExplainer, CommandHelp, CommandGroupHelp, LocaleName

__all__: tuple = ('GitBotCommand', 'GitBotCommandGroup')


class GitBotCommand(commands.Command):
    def __init__(self, func: Callable, **kwargs):
        super().__init__(func, **kwargs)
        self._cached_help_contents: dict[LocaleName, CommandHelp] = {}

    @property
    def fullname(self) -> str:
        return self.name if not self.full_parent_name else f'{self.full_parent_name} {self.name}'

    @property
    def underscored_name(self) -> str:
        return self.fullname.lower().replace(' ', '_')

    def get_argument_explainers(self, ctx: 'GitBotContext') -> Generator[ArgumentExplainer, None, None]:
        for explainer in self.get_help_content(ctx)['argument_explainers']:
            yield ctx.l.help.argument_explainers[explainer]

    def get_qa_disclaimer(self, ctx: 'GitBotContext') -> Optional[str]:
        return ctx.l.help.qa_disclaimers.get(self.get_help_content(ctx)['qa_resource'])

    def get_permissions(self, ctx: 'GitBotContext') -> Generator[str, None, None]:
        for permission_resource_name in self.get_help_content(ctx)['required_permissions']:
            yield ctx.l.permissions[permission_resource_name]

    def get_help_content(self, ctx: 'GitBotContext') -> Optional[CommandHelp]:
        if cached := self._cached_help_contents.get(ctx.l.meta.name):
            return cached
        help_: CommandHelp = ctx.l.help.commands.get(self.underscored_name)
        if not help_:
            return
        if not help_['usage']:
            help_['usage'] = self.fullname
        self._cached_help_contents[ctx.l.meta.name] = help_
        return help_

    def __str__(self) -> str:
        return self.fullname

    def __repr__(self) -> str:
        return self.__str__()


class GitBotCommandGroup(commands.Group, GitBotCommand):
    def __init__(self, func, **attrs):
        super().__init__(func, **attrs)

    def command(self, name: str = '', **kwargs) -> Callable:
        def decorator(func: Callable) -> GitBotCommand:
            kwargs.setdefault('parent', self)
            if name:
                kwargs.setdefault('name', name)
            result: GitBotCommand = GitBotCommand(func, **kwargs)
            self.add_command(result)
            return result

        return decorator

    def group(self, name: str = '', **kwargs) -> Callable:
        def decorator(func: Callable) -> GitBotCommandGroup:
            kwargs.setdefault('parent', self)
            if name:
                kwargs.setdefault('name', name)
            result: GitBotCommandGroup = GitBotCommandGroup(func, **kwargs)
            self.add_command(result)
            return result

        return decorator

    def get_help_content(self, ctx: 'GitBotContext', command_contents: bool = False) -> Optional[CommandGroupHelp]:
        help_: CommandHelp | CommandGroupHelp = super().get_help_content(ctx)
        if not help_:
            return
        help_.setdefault('commands', self.commands if not command_contents else [cmd.get_help_content(ctx)
                                                                                 for cmd in self.commands])
        return help_
