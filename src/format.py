import re
import subprocess

import sublime
import sublime_plugin

from .settings import (
    PKG_SETTINGS_KEY_ENABLED,
    PKG_SETTINGS_KEY_EXCLUDE,
    PKG_SETTINGS_KEY_EXTEND_EXCLUDE,
    PKG_SETTINGS_KEY_EXTEND_INCLUDE,
    PKG_SETTINGS_KEY_INCLUDE,
    pkg_settings,
)
from .sublime_extra import platform_startupinfo

# @todo #0 Why does cursor position advance forward after each save when using e.g.
#  pg_format on the .sql file:
#  CREATE TABLE persons (
#  personid INT
#  , lastname VARCHAR(255)
#  , firstname VARCHAR(255)
#  , address VARCHAR(255)
#  , city VARCHAR(255)
#  );


class PreSaveFormat(sublime_plugin.TextCommand):

    TXT_ENCODING = "utf-8"

    # Overrides --------------------------------------------------

    def run(self, edit, command, append_file_path_to_command=False, **_):
        try:
            self.run_core(edit, command, append_file_path_to_command)
        except Exception as e:
            sublime.error_message(str(e))

    # ------------------------------------------------------------

    def run_core(self, edit, command, append_file_path_to_command):
        view_region = sublime.Region(0, self.view.size())
        view_content = self.view.substr(view_region)
        view_content_started_empty = len(view_content) == 0

        view_file_path = self.view.file_name()
        if append_file_path_to_command:
            command.append(view_file_path)

        # Allow e.g. numbers to be unquoted in the settings file (4 instead of "4")
        command = [str(component) for component in command]

        print(  # noqa: T001
            "[{0}] Running process {1} fed with content of view {2}".format(
                PreSaveFormat.__name__, command, view_file_path
            )
        )
        child_proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=platform_startupinfo(),
        )
        stdout_content_bytes, stderr_content_bytes = child_proc.communicate(
            input=bytes(view_content, self.TXT_ENCODING)
        )
        stdout_content, stderr_content = (
            stdout_content_bytes.decode(self.TXT_ENCODING),
            self.postprocess_stderr(stderr_content_bytes.decode(self.TXT_ENCODING)),
        )

        if child_proc.returncode != 0:
            print(  # noqa: T001
                "\n\n*** [{0}] stderr of `{1}` was:\n\n{2}\n\n".format(
                    PreSaveFormat.__name__, command[0], stderr_content
                )
            )
            sublime.set_timeout(
                lambda: sublime.status_message(
                    "{0} failed - see console".format(command[0]).upper()
                ),
                100,
            )
            return

        if not len(stdout_content) and not view_content_started_empty:
            raise Exception(
                "[{0}] '{1}' command produced no output "
                "despite exiting successfully.".format(
                    PreSaveFormat.__name__, command[0]
                )
            )
        self.view.replace(edit, view_region, stdout_content)

    def postprocess_stderr(self, s):
        # Remove ANSI colour codes
        s = re.sub("\x1b\\[\\d{1,2}m", "", s)  # noqa: FS003
        return s.strip()


# @todo #0 Key the settings file on pos0 scope selectors (like BuildOnSave) rather than
#  path of view's syntax definition. That way, stuff like JS & TS, C & C++ can share one
#  settings block that has an appropriate selector, rather than duplicating blocks.


class PreSaveListener(sublime_plugin.ViewEventListener):

    # Overrides --------------------------------------------------

    @classmethod
    def is_applicable(cls, settings):
        return cls.settings_for_view_language(settings) is not None

    @classmethod
    def applies_to_primary_view_only(cls):
        return False

    def on_pre_save(self):
        try:
            lang_settings = self.settings_for_view_language(self.view.settings())
            if isinstance(lang_settings, list):
                steps = lang_settings
            else:
                steps = [lang_settings]

            for step in steps:
                if self.should_format(self.view.file_name(), step):
                    self.view.run_command(PreSaveFormat(None).name(), step)
        except Exception as e:
            sublime.error_message(str(e))

    # ------------------------------------------------------------

    @classmethod
    def settings_for_view_language(cls, view_settings):
        view_syntax_path = view_settings.get("syntax")
        return pkg_settings().get(view_syntax_path)

    def load_extensible_settings_list(self, priority_settings, key, extension_key):
        lst = priority_settings.get(key, pkg_settings().get(key))
        lst.extend(
            priority_settings.get(extension_key, pkg_settings().get(extension_key, []))
        )
        return lst

    def should_format(self, path, lang_settings):
        if not lang_settings.get(PKG_SETTINGS_KEY_ENABLED, True):
            return False

        includes = self.load_extensible_settings_list(
            lang_settings, PKG_SETTINGS_KEY_INCLUDE, PKG_SETTINGS_KEY_EXTEND_INCLUDE
        )
        excludes = self.load_extensible_settings_list(
            lang_settings, PKG_SETTINGS_KEY_EXCLUDE, PKG_SETTINGS_KEY_EXTEND_EXCLUDE
        )

        # @todo #0 Use Python stdlib "glob" rather than basic substring matching.
        #  And add a comment in the default settings file explaining the logic.
        include_hits = [fragment in path for fragment in includes]
        exclude_hits = [fragment in path for fragment in excludes]
        return any(include_hits) and not any(exclude_hits)
