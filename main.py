import subprocess
import os
import re
import shlex
import shutil
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction

# File extension sets
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv'}
PICTURE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}

def find_plocate(search, max_results=50, use_regex=True, regex_pattern=None):
    """Search files using plocate or locate with optional regex."""
    if not search:
        return []

    plocate_path = shutil.which("plocate") or shutil.which("locate")
    if not plocate_path:
        print("[QuickLocate ERROR] plocate/locate not found in PATH")
        return []

    if use_regex:
        if not regex_pattern:
            regex_pattern = rf'.*{re.escape(search)}.*'
        cmd = f'{plocate_path} -r -i {shlex.quote(regex_pattern)}'
    else:
        cmd = f'{plocate_path} {shlex.quote(search)}'

    print(f"[QuickLocate DEBUG] Running command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stderr:
            print(f"[QuickLocate DEBUG] STDERR: {result.stderr.strip()}")
        if result.returncode != 0:
            print(f"[QuickLocate DEBUG] Command failed with code {result.returncode}")
            return []
        paths = result.stdout.splitlines()
        print(f"[QuickLocate DEBUG] Raw output ({len(paths)} lines): {paths[:10]}")
        return paths[:max_results]
    except Exception as e:
        print(f"[QuickLocate ERROR] Exception while running plocate: {e}")
        return []

def get_item(path, label=None, small=True):
    """Build a Ulauncher item: filename on top, path below."""
    filename = os.path.basename(path) if not label else label
    if small:
        return ExtensionSmallResultItem(
            icon="images/xxxs_icon.png",
            name=filename,
            on_enter=RunScriptAction(f'xdg-open "{path}"', [])
        )
    else:
        return ExtensionResultItem(
            icon="images/xxs_icon.png",
            name=filename,
            description=path,
            on_enter=RunScriptAction(f'xdg-open "{path}"', [])
        )

def prioritize_results(paths, query):
    """Prioritize search results: exact, whole-word, then partial match."""
    query_lower = query.lower()
    exact, word_match, partial = [], [], []

    for p in paths:
        filename = os.path.basename(p).lower()
        if filename == query_lower:
            exact.append(p)
        elif re.search(rf'\b{re.escape(query_lower)}\b', filename):
            word_match.append(p)
        elif query_lower in filename:
            partial.append(p)
    return exact + word_match + partial

class QuickLocateExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, QuickLocateEventListener())

class QuickLocateEventListener(EventListener):
    def on_event(self, event, extension):
        query = event.get_argument()
        keyword = event.get_keyword()
        print(f"[QuickLocate DEBUG] Event triggered: query='{query}', keyword='{keyword}'")

        qf_keyword = extension.preferences.get('qf')
        qvid_keyword = extension.preferences.get('qv')
        qp_keyword = extension.preferences.get('qp')
        qa_keyword = extension.preferences.get('qa')
        qdir_keyword = extension.preferences.get('qdir')
        cut_off = int(extension.preferences.get('cut', 30))
        min_length = int(extension.preferences.get('min_len', 3))
        cut_off_factor = 10
        found = []

        if query and len(query) >= min_length:

            # -------- File search --------
            if keyword == qf_keyword:
                print("[QuickLocate DEBUG] Performing file search")
                raw_files = find_plocate(query, max_results=cut_off*cut_off_factor, use_regex=True)
                found = prioritize_results(raw_files, query)
                found = found[:cut_off]


            # -------- Video search --------
            elif keyword == qvid_keyword:
                print("[QuickLocate DEBUG] Performing video file search")
                video_regex = rf'.*{re.escape(query)}.*\({ "\|".join(ext[1:] for ext in VIDEO_EXTENSIONS) }\)'
                raw_files = find_plocate(query, max_results=cut_off*cut_off_factor, use_regex=True, regex_pattern=video_regex)
                found = prioritize_results(raw_files, query)
                found = found[:cut_off]

            # -------- Picture search --------
            elif keyword == qp_keyword:
                print("[QuickLocate DEBUG] Performing picture file search")
                pic_regex   = rf'.*{re.escape(query)}.*\({ "\|".join(ext[1:] for ext in PICTURE_EXTENSIONS) }\)'
                raw_files = find_plocate(query, max_results=cut_off*cut_off_factor, use_regex=True, regex_pattern=pic_regex)
                found = prioritize_results(raw_files, query)
                found = found[:cut_off]

            # -------- Audio search --------
            elif keyword == qa_keyword:
                print("[QuickLocate DEBUG] Performing audio file search")
                audio_regex = rf'.*{re.escape(query)}.*\({ "\|".join(ext[1:] for ext in AUDIO_EXTENSIONS) }\)'
                raw_files = find_plocate(query, max_results=cut_off*cut_off_factor, use_regex=True, regex_pattern=audio_regex)
                found = prioritize_results(raw_files, query)
                found = found[:cut_off]

            # -------- Directory search --------
            elif keyword == qdir_keyword:
                print("[QuickLocate DEBUG] Performing directory search")
                dir_regex = rf'.*{re.escape(query)}.*'
                raw_dirs = [p for p in find_plocate(query, max_results=cut_off*cut_off_factor, use_regex=True, regex_pattern=dir_regex) if os.path.isdir(p)]
                found = prioritize_results(raw_dirs, query)
                found = found[:cut_off]

        else:
            print(f"[QuickLocate DEBUG] Query too short, ignoring: '{query}'")

        # ---------------- Build Ulauncher items ----------------
        items = []
        if not found:
            items.append(ExtensionResultItem(
                icon="images/xxs_icon.png",
                name="No results found",
                description=f"Query: {query}",
                on_enter=None
            ))
        else:
            for path in found:
                if cut_off > 15:
                    items.append(get_item(path, small=True))
                else:
                    items.append(get_item(path, small=False))

        return RenderResultListAction(items)

if __name__ == '__main__':
    QuickLocateExtension().run()
