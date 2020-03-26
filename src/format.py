import sublime
import sublime_plugin
from .sublime_extra import platform_startupinfo, command_name_from_class

import re
import subprocess

from .pkg_settings import (
    pkg_settings,
    PKG_SETTINGS_KEY_ENABLED,
    PKG_SETTINGS_KEY_INCLUDE,
    PKG_SETTINGS_KEY_EXCLUDE,
)


class PreSaveFormat(sublime_plugin.TextCommand):

    TXT_ENCODING = "utf-8"

    # Overrides --------------------------------------------------

    def run(self, edit, command_line, append_file_path_to_command_line, **_):
        try:
            self.run_core(edit, command_line, append_file_path_to_command_line)
        except Exception as e:
            sublime.error_message(str(e))

    # ------------------------------------------------------------

    def run_core(self, edit, command_line, append_file_path_to_command_line):
        view_region = sublime.Region(0, self.view.size())
        view_content = self.view.substr(view_region)
        view_content_started_empty = len(view_content) == 0

        view_file_path = self.view.file_name()
        if append_file_path_to_command_line:
            command_line.append(view_file_path)

        print(  # noqa: T001
            "[{0}] Running {1} fed with content of view {2}".format(
                PreSaveFormat.__name__, command_line, view_file_path
            )
        )
        child_proc = subprocess.Popen(
            command_line,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=platform_startupinfo(),
        )
        stdout_content, stderr_content = child_proc.communicate(
            input=bytes(view_content, self.TXT_ENCODING)
        )
        stdout_content, stderr_content = (
            stdout_content.decode(self.TXT_ENCODING),
            self.postprocess_stderr(stderr_content.decode(self.TXT_ENCODING)),
        )

        if child_proc.returncode != 0:
            print(  # noqa: T001
                "\n\n*** [{0}] stderr of `{1}` was:\n\n{2}\n\n".format(
                    PreSaveFormat.__name__, command_line[0], stderr_content
                )
            )
            sublime.set_timeout(
                lambda: sublime.status_message(
                    "{0} failed - see console".format(command_line[0]).upper()
                ),
                100,
            )
            return

        if not len(stdout_content) and not view_content_started_empty:
            raise Exception(
                "[{0}] '{1}' command produced no output "
                "despite exiting successfully.".format(
                    PreSaveFormat.__name__, command_line[0]
                )
            )
        self.view.replace(edit, view_region, stdout_content)

    def postprocess_stderr(self, s):
        # Remove ANSI colour codes
        s = re.sub("\x1b\\[\\d{1,2}m", "", s)
        return s.strip()


class PreSaveListener(sublime_plugin.ViewEventListener):

    # Overrides --------------------------------------------------

    @classmethod
    def is_applicable(cls, settings):
        return cls.settings_for_view_language(settings) is not None

    def on_pre_save(self):
        try:
            lang_settings = self.settings_for_view_language(self.view.settings())
            if self.should_format(self.view.file_name(), lang_settings):
                self.view.run_command(
                    command_name_from_class(PreSaveFormat), lang_settings
                )
        except Exception as e:
            sublime.error_message(str(e))

    # ------------------------------------------------------------

    @classmethod
    def settings_for_view_language(cls, view_settings):
        view_syntax_path = view_settings.get("syntax")
        return pkg_settings().get(view_syntax_path)

    def should_format(self, path, lang_settings):
        if not lang_settings.get(PKG_SETTINGS_KEY_ENABLED, True):
            return False

        # @todo #0 Use Python stdlib "glob" rather than basic substring matching.
        #  And add a comment in the default settings file explaining the logic.
        include_hits = [
            fragment in path for fragment in lang_settings.get(PKG_SETTINGS_KEY_INCLUDE)
        ]
        exclude_hits = [
            fragment in path for fragment in lang_settings.get(PKG_SETTINGS_KEY_EXCLUDE)
        ]
        return any(include_hits) and not any(exclude_hits)
