import sublime
import sublime_plugin

import re
import subprocess
import sys


class ElmFormat(sublime_plugin.TextCommand):

    COMMAND_LINE = ["elm-format", "--stdin", "--yes"]
    TXT_ENCODING = "utf-8"

    # Overrides --------------------------------------------------

    def run(self, edit):
        try:
            self.run_core(edit)
        except Exception as e:
            sublime.error_message(str(e))

    # ------------------------------------------------------------

    def run_core(self, edit):
        view_region = sublime.Region(0, self.view.size())
        view_content = self.view.substr(view_region)

        child_proc = subprocess.Popen(
            self.COMMAND_LINE,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=self.platform_startupinfo(),
        )
        stdout_content, stderr_content = child_proc.communicate(
            input=bytes(view_content, self.TXT_ENCODING)
        )
        stdout_content, stderr_content = (
            stdout_content.decode(self.TXT_ENCODING),
            stderr_content.decode(self.TXT_ENCODING),
        )

        if child_proc.returncode != 0:
            # Remove any ANSI colour codes
            stderr_content = re.sub("\x1b\\[\\d{1,2}m", "", stderr_content)
            stderr_content = stderr_content.strip()
            print("\n\n{0}\n\n".format(stderr_content))  # noqa: T001
            sublime.set_timeout(
                lambda: sublime.status_message(
                    "{0} failed - see console".format(self.COMMAND_LINE[0]).upper()
                ),
                100,
            )
            return

        if not len(stdout_content):
            raise Exception(
                "{0} produced no output despite exiting successfully".format(
                    self.COMMAND_LINE[0]
                )
            )
        self.view.replace(edit, view_region, stdout_content)

    def platform_startupinfo(self):
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            # Stop a visible console window from appearing.
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            return si
        else:
            return None


class ElmFormatPreSave(sublime_plugin.ViewEventListener):

    SETTINGS_BASENAME = "ElmFormatPreSave.sublime-settings"
    SETTINGS_KEY_ENABLED = "enabled"
    SETTINGS_KEY_INCLUDE = "include"
    SETTINGS_KEY_EXCLUDE = "exclude"

    # Overrides --------------------------------------------------

    @classmethod
    def is_applicable(cls, settings):
        return settings.get("syntax") == "Packages/ElmFeather/Elm.tmLanguage"

    def on_pre_save(self):
        try:
            if self.should_format(self.view.file_name()):
                self.view.run_command("elm_format")
        except Exception as e:
            sublime.error_message(str(e))

    # ------------------------------------------------------------

    def should_format(self, path):
        settings = sublime.load_settings(self.SETTINGS_BASENAME)
        enabled = settings.get(self.SETTINGS_KEY_ENABLED)
        if enabled is None:
            raise Exception(
                '"{0}" should have an "{1}" key'.format(
                    self.SETTINGS_BASENAME, self.SETTINGS_KEY_ENABLED
                )
            )
        if not enabled:
            return False

        # @todo #0 Use Python stdlib "glob" rather than basic substring matching.
        #  And add a comment in the default settings file explaining the logic.
        include_hits = [
            fragment in path for fragment in settings.get(self.SETTINGS_KEY_INCLUDE)
        ]
        exclude_hits = [
            fragment in path for fragment in settings.get(self.SETTINGS_KEY_EXCLUDE)
        ]
        return any(include_hits) and not any(exclude_hits)
