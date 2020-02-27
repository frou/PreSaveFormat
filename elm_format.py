import os
import os.path
import re
import sublime
import sublime_plugin
import subprocess


class ElmFormatCommand(sublime_plugin.TextCommand):

    TXT_ENCODING = "utf-8"

    # Overrides --------------------------------------------------

    def run(self, edit):
        region = sublime.Region(0, self.view.size())
        content = self.view.substr(region)

        stdout, stderr = subprocess.Popen(
            ["elm-format", "--stdin", "--yes"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=os.name == "nt",
        ).communicate(input=bytes(content, self.TXT_ENCODING))

        errstr = stderr.strip().decode(self.TXT_ENCODING)
        errstr = re.sub("\x1b\\[\\d{1,2}m", "", errstr)  # Strip ANSI colour codes
        if errstr:
            print("\n\n{0}\n\n".format(errstr))  # noqa: T001
            sublime.set_timeout(
                lambda: sublime.status_message("ELM-FORMAT FAILED - SEE CONSOLE"), 100
            )
        else:
            self.view.replace(edit, region, stdout.decode("UTF-8"))


class ElmFormatOnSave(sublime_plugin.ViewEventListener):

    SETTINGS_BASENAME = "elm-format-on-save.sublime-settings"
    SETTINGS_KEY_ONSAVE = "on_save"

    # Overrides --------------------------------------------------

    @classmethod
    def is_applicable(cls, settings):
        return settings.get("syntax") == "Packages/ElmFeather/Elm.tmLanguage"

    def on_pre_save(self):
        try:
            if self.needs_format(self.view):
                self.view.run_command("elm_format")
        except Exception as e:
            sublime.error_message(e)

    # ------------------------------------------------------------

    def needs_format(self):

        settings = sublime.load_settings(self.SETTINGS_BASENAME)
        on_save = settings.get(self.SETTINGS_KEY_ONSAVE, True)

        if isinstance(on_save, bool):
            return on_save
        elif isinstance(on_save, dict):
            path = self.view.file_name()
            included = is_included(on_save, path)
            excluded = is_excluded(on_save, path)
            if isinstance(included, bool) and isinstance(excluded, bool):
                return included and not excluded
        else:
            raise Exception(
                '"{0}" in "{1}" has an invalid value'.format(
                    self.SETTINGS_KEY_ONSAVE, self.SETTINGS_BASENAME
                )
            )


def is_included(on_save, path):
    if "including" in on_save:
        if not isinstance(on_save.get("including"), list):
            return None

        for string in on_save.get("including"):
            if string in path:
                return True

        return False

    return True


def is_excluded(on_save, path):
    if "excluding" in on_save:
        if not isinstance(on_save.get("excluding"), list):
            return None

        for string in on_save.get("excluding"):
            if string in path:
                return True

        return False

    return False
