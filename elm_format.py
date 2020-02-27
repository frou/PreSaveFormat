import os
import os.path
import re
import sublime
import sublime_plugin
import subprocess


#### COMMAND ####


class ElmFormatCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        region = sublime.Region(0, self.view.size())
        content = self.view.substr(region)
        TXT_ENCODING = "utf-8"

        stdout, stderr = subprocess.Popen(
            ["elm-format", "--stdin", "--yes"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=os.name == "nt",
        ).communicate(input=bytes(content, TXT_ENCODING))

        errstr = stderr.strip().decode(TXT_ENCODING)
        errstr = re.sub("\x1b\\[\\d{1,2}m", "", errstr)  # Strip ANSI colour codes
        if errstr:
            print("\n\n{0}\n\n".format(errstr))
            sublime.set_timeout(
                lambda: sublime.status_message("ELM-FORMAT FAILED - SEE CONSOLE"), 100
            )
        else:
            self.view.replace(edit, region, stdout.decode("UTF-8"))


#### ON SAVE ####


class ElmFormatOnSave(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return settings.get("syntax") == "Packages/ElmFeather/Elm.tmLanguage"

    def on_pre_save(self):
        if not needs_format(self.view):
            return
        self.view.run_command("elm_format")


def needs_format(view):
    SETTINGS_BASENAME = "elm-format-on-save.sublime-settings"
    SETTINGS_KEY_ONSAVE = "on_save"

    settings = sublime.load_settings(SETTINGS_BASENAME)
    on_save = settings.get(SETTINGS_KEY_ONSAVE, True)

    if isinstance(on_save, bool):
        return on_save

    if isinstance(on_save, dict):
        path = view.file_name()
        included = is_included(on_save, path)
        excluded = is_excluded(on_save, path)
        if isinstance(included, bool) and isinstance(excluded, bool):
            return included and not excluded

    sublime.message_dialog(
        '"{0}" in "{1}" has an invalid value'.format(
            SETTINGS_KEY_ONSAVE, SETTINGS_BASENAME
        )
    )
    return False


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
