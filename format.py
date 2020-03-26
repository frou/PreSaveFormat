import sublime
import sublime_plugin

import re
import subprocess
import sys


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

        view_file_path = self.view.file_name()
        if append_file_path_to_command_line:
            command_line.append(view_file_path)

        print(  # noqa: T001
            "[{0}] Running {1} with view content from {2}".format(
                PreSaveFormat.__name__, command_line, view_file_path
            )
        )
        child_proc = subprocess.Popen(
            command_line,
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

        # @todo #0 Don't complain about no stdout content if the view content was empty
        #  to start with.
        if not len(stdout_content):
            raise Exception(
                "{0} produced no output despite exiting successfully".format(
                    command_line[0]
                )
            )
        self.view.replace(edit, view_region, stdout_content)

    def postprocess_stderr(self, s):
        # Remove ANSI colour codes
        s = re.sub("\x1b\\[\\d{1,2}m", "", s)
        return s.strip()

    def platform_startupinfo(self):
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            # Stop a visible console window from appearing.
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            return si
        else:
            return None


class PreSaveListener(sublime_plugin.ViewEventListener):

    PKG_SETTINGS_BASENAME = "{0}.sublime-settings".format(PreSaveFormat.__name__)
    # @todo #0 The API docs make it sound like using sublime.load_settings(...) once
    #  returns a live object that will reflect the settings file on disk changing,
    #  but that doesn't always seem to be the case.
    PKG_SETTINGS = sublime.load_settings(PKG_SETTINGS_BASENAME)
    PKG_SETTINGS_KEY_ENABLED = "enabled"
    PKG_SETTINGS_KEY_INCLUDE = "include"
    PKG_SETTINGS_KEY_EXCLUDE = "exclude"

    # Overrides --------------------------------------------------

    @classmethod
    def is_applicable(cls, settings):
        return cls.settings_for_view_language(settings) is not None

    def on_pre_save(self):
        try:
            lang_settings = self.settings_for_view_language(self.view.settings())
            if self.should_format(self.view.file_name(), lang_settings):
                self.view.run_command("pre_save_format", lang_settings)
        except Exception as e:
            sublime.error_message(str(e))

    # ------------------------------------------------------------

    @classmethod
    def settings_for_view_language(cls, view_settings):
        view_syntax_path = view_settings.get("syntax")
        return cls.PKG_SETTINGS.get(view_syntax_path)

    def should_format(self, path, lang_settings):
        if not lang_settings.get(self.PKG_SETTINGS_KEY_ENABLED, True):
            return False

        # @todo #0 Use Python stdlib "glob" rather than basic substring matching.
        #  And add a comment in the default settings file explaining the logic.
        include_hits = [
            fragment in path
            for fragment in lang_settings.get(self.PKG_SETTINGS_KEY_INCLUDE)
        ]
        exclude_hits = [
            fragment in path
            for fragment in lang_settings.get(self.PKG_SETTINGS_KEY_EXCLUDE)
        ]
        return any(include_hits) and not any(exclude_hits)
