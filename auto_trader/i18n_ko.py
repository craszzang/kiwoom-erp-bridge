"""Korean UI strings (unicode escapes, encoding-safe)."""

WIN_TITLE = "\uc0dd\uc0b0\uc9c0\uc2dc\ud604\ud669_2026.xlsx - Excel"
FORMULA_TITLE = "\u25c6 \ubcf8\uc0ac \uc0dd\uc0b0\uc9c0\uc2dc \ud604\ud669 (\ub0a9\ud488\uc9c0\uc2dc)"
SHEET_TITLE = FORMULA_TITLE
META_FMT = (
    "\uc791\uc131\uc77c: {date}  |  \ub2f4\ub2f9: \uc601\uc5c5\ud300  |  "
    "\ud544\ud130: \ub9e4\ub3c4\uc794\ub7c9 {sell_pct:.0f}% \u2191  \uccb4\uacb0\uac15\ub3c4 {strength:.0f} \u2191"
)

COL_HEADERS = [
    "\uc791\uc9c0",
    "\ub0a9\uae30",
    "\ud488\ubaa9\ud604\ud669",
    "EA",
    "\ub0a9\ud488\ucc98\uba85",
    "\ub2f4\ub2f9\uc790",
    "\uc9c4\ud589\uc644\ub8cc",
    "\ud310\ub9e4\uac00\uaca9",
    "\ub4f1\ub77d\ub960",
    "\uc608\uc0c1\ub9e4\uc218\uae08\uc561",
    "\uc218\ub7c9",
    "\uc2dc\uc7a5\ub9e4\uc218",
    "\uc2dc\uc7a5\ub9e4\ub3c4",
    "\uc9c0\uc815\uac00\ub9e4\uc218",
    "\uc9c0\uc815\uac00\ub9e4\ub3c4",
    "\ud3c9\uac00\uc190\uc775",
    "\uc190\uc775%",
    "\uc2e4\ud604\uc774\uc775",
    "\uc2e4\ud604%",
    "\uc601\uc5c5\ub9e4\ucd9c",
    "\uccb4\uacb0\uac15\ub3c4",
]

# Column index constants (keep in sync with COL_HEADERS)
COL_VENDOR = 4
COL_STATUS = 6
COL_PRICE = 7
COL_CHANGE = 8
COL_EST_AMOUNT = 9
COL_QTY = 10
COL_MKT_BUY = 11
COL_MKT_SELL = 12
COL_LMT_BUY = 13
COL_LMT_SELL = 14
COL_PNL = 15
COL_PNL_PCT = 16
COL_REALIZED = 17
COL_REALIZED_PCT = 18
COL_SELL_BAL = 19
COL_STRENGTH = 20

HEADER_BG = "#404040"
HEADER_FG = "#FFFFFF"
ROW_COLOR_BLOCKS = (
    ("#D9EAF7", 5),
    ("#FCE4D6", 4),
    ("#E2EFDA", 3),
    ("#F8CBAD", 2),
    ("#E1D5E7", 8),
)
PNL_PLUS = "#C00000"
PNL_MINUS = "#0070C0"

LBL_FILTER_BAR_SELL = "\ub9e4\ub3c4\uc794\ub7c9%"
LBL_FILTER_BAR_STRENGTH = "\uccb4\uacb0\uac15\ub3c4"
BTN_FILTER_APPLY = "\uc801\uc6a9"
BTN_MKT_BUY = "\uc2dc\uc7a5\ub9e4\uc218"
BTN_MKT_SELL = "\uc2dc\uc7a5\ub9e4\ub3c4"
BTN_LMT_BUY = "\ub9e4\uc218"
BTN_LMT_SELL = "\ub9e4\ub3c4"
PH_LIMIT_PRICE = "\uac00\uaca9"
PH_QTY = "\uc218\ub7c9"
EST_AMOUNT_FMT = "{amount:,}\uc6d0"
CHANGE_FMT = "{pct:+.2f}%"
CHANGE_AMT_FMT = "{pct:+.2f}% ({amt:+,})"
F_CHANGE = "\uc804\uc77c\ub300\ube44"
F_CHANGE_RATE = "\ub4f1\ub77d\uc728"
MSG_ORDER_SENT = "\uc8fc\ubb38 \uc804\uc1a1: {name}"
MSG_ORDER_FAIL = "\uc8fc\ubb38 \uc2e4\ud328 (code={code})"
MSG_NEED_CONNECT = "F5\ub85c \uba3c\uc800 \uc5f0\ub3d9\ud574 \uc8fc\uc138\uc694."
MSG_BAD_PRICE = "\uc9c0\uc815\uac00\ub97c \uc785\ub825\ud558\uc138\uc694."

DECOY_ROWS = [
    (
        "2026/05/13-5",
        "2026-05-20",
        "S100*11700",
        "200",
        "\ub3d9\uc778\uc911\uacf5\uc5c5 \uc8fc\uc2dd\ud68c\uc0ac",
        "\uc774\uc601\uc218 \ub300\ub9ac",
        "6-15-3\uc644",
        "2,960",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "592,000",
        "-",
    ),
    (
        "2026/05/14-2",
        "2026-05-22",
        "SUS304 \uac04\uc774",
        "60",
        "\uace0\ub824\ud14c\ud06c",
        "\uae40\uc815\ud658 \uc0ac\uc6d0",
        "",
        "120,000",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "7,200,000",
        "-",
    ),
    (
        "2026/05/15-1",
        "2026-05-25",
        "SM45C \ubc14",
        "100",
        "\ud604\ub300\uc81c\ucca0(\uc8fc)\uc778\ucc9c",
        "\ubc15\uc131\ud6c8 \ud300\uc7a5",
        "",
        "76,000",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "7,600,000",
        "-",
    ),
    (
        "2026/05/16-3",
        "2026-05-28",
        "AL6061 \ud310",
        "40",
        "\uc5d8\uc5d0\uc2a4\uc5e0\ud2b8\ub860(\uc8fc)",
        "\ucd5c\ubbfc\uc11c \uc8fc\uc784",
        "",
        "45,500",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "1,820,000",
        "-",
    ),
    (
        "2026/05/17-2",
        "2026-05-30",
        "S45C \uc548\uc9c4",
        "80",
        "\uc0bc\uc131\uc911\uacf5\uc5c5",
        "\uc815\ub300\ud658 \uacfc\uc7a5",
        "",
        "38,200",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "3,056,000",
        "-",
    ),
]

MENU_NAMES = (
    "\ud30c\uc77c(F)",
    "\ud3b8\uc9d1(E)",
    "\ubcf4\uae30(V)",
    "\uc0bd\uc785(I)",
    "\ub370\uc774\ud130(D)",
    "\uac80\ud1a0(R)",
    "\ub3c4\uc6c0\ub9d0(H)",
)
RIBBON_TABS = ("\ud30c\uc77c", "\ud648", "\uc0bd\uc785", "\uc218\uc2dd", "\ub370\uc774\ud130")
TOOL_BTNS = (
    "\uc800\uc7a5",
    "\uc2e4\ud589\ucde8\uc18c",
    "\ubd99\uc5ec\ub123\uae30",
    "\uad75\uac8c",
    "\uac00\uc6b4\ub370\ub9de\ucda4",
    "\ud569\uacc4",
    "\uc815\ub82c",
    "\uc0c8\ub85c\uace0\uce68",
)
SHEET_TABS = ("\uc0dd\uc0b0\uc9c0\uc2dc", "\ub0a9\ud488\uc9c0\uc2dc", "\uac70\ub798\ucc98\ubaa9\ub85d")

STATUS_WAIT = "\ub300\uae30"
STATUS_LINKED = "\uc5f0\ub3d9\ub428"
STATUS_PRESS_F5 = "F5 \ub610\ub294 \ub9ac\ubcf8 [\uc0c8\ub85c\uace0\uce68] \uc744 \ub20c\ub7ec ERP \uc5f0\ub3d9\uc744 \uc2dc\uc791\ud558\uc138\uc694"
MSG_PRESS_F5 = (
    "ERP \uc5f0\ub3d9\uc744 \uc2dc\uc791\ud569\ub2c8\ub2e4.\n\n"
    "1) \uc774 \ucc3d\uc5d0\uc11c F5 \ud0a4 \ub610\ub294\n"
    "   \uc0c1\ub2e8 \ub9ac\ubcf8 [\uc0c8\ub85c\uace0\uce68] \ubc84\ud2bc \ud074\ub9ad\n"
    "2) \uc548\ub0b4 \ucc3d \ud655\uc778\n"
    "3) \ud0a4\uc6c0 \ub85c\uadf8\uc778 (\ubaa8\uc758\ud22c\uc790 \uccb4\ud06c)\n"
    "4) \uc870\uac74\uc2dd \uc120\ud0dd"
)
MSG_PRESS_F5_REMOTE = (
    "\uc6d0\uaca9 ERP \ubaa8\ub4dc\uc785\ub2c8\ub2e4.\n\n"
    "F5 \ub610\ub294 \uc0c1\ub2e8 [\uc0c8\ub85c\uace0\uce68] \uc744 \ub20c\ub7ec\n"
    "\ud638\uc2a4\ud2b8 PC \ube0c\ub9bf\uc9c0\uc5d0 \uc5f0\uacb0\ud558\uc138\uc694.\n\n"
    "\u203b \ud638\uc2a4\ud2b8: \ube0c\ub9bf\uc9c0-\ucf1c\uae30 + \ud0a4\uc6c0 \ub85c\uadf8\uc778 \uc644\ub8cc"
)
MSG_CONN_FIRST = "F5\ub85c \uba3c\uc800 ERP \uc5f0\ub3d9\uc744 \ud574 \uc8fc\uc138\uc694."
MSG_COND_APPLIED = "\uc870\uac74\uc2dd \uc801\uc6a9: {names}"
MENU_COND_PICK = "\uc870\uac74\uc2dd \uc120\ud0dd..."
MENU_FILTER = "\ud544\ud130 \uc124\uc815..."
MENU_ACCOUNT_PW = "\uacc4\uc88c\ube44\ubc00\ubc88\ub4f1\ub85d..."
MSG_ACCOUNT_PW_HINT = (
    "\uc8fc\ubb38\uc744 \ub0b4\ub824\uba74 \uacc4\uc88c\ube44\ubc00\ubc88\uc744 OpenAPI\uc5d0 \ub4f1\ub85d\ud574\uc57c \ud569\ub2c8\ub2e4.\n\n"
    "\uc9c0\uae08 \ub728\ub294 \ucc3d\uc5d0\uc11c \ubaa8\uc758\ud22c\uc790 \uacc4\uc88c\ub97c \uc120\ud0dd\ud558\uace0\n"
    "\ube44\ubc00\ubc88\ud638\ub97c \uc785\ub825\ud55c \ub4a4 [\ub4f1\ub85d] \uc744 \ub20c\ub7ec \uc8fc\uc138\uc694.\n\n"
    "(\uc601\uc6c1\ubb38 \uc124\uc815 \u2192 Open API \u2192 \uacc4\uc88c\ube44\ubc00\ubc88 \ub4f1\ub85d\uc5d0\uc11c\ub3c4 \uac00\ub2a5)"
)
MSG_FILTER_PASS_ONLY_HINT = (
    "\uc870\uac74\uc2dd {total}\uac74 \uc911 \ud544\ud130 \ud1b5\uacfc {passed}\uac74\ub9cc \ud45c\uc2dc \uc911\uc785\ub2c8\ub2e4.\n"
    "\uc804\uccb4 \ubcf4\ub824\uba74 \uc0c1\ub2e8 [\ud544\ud130 \ud1b5\uacfc \uc885\ubaa9\ub9cc \ud45c\uc2dc] \uccb4\ud06c\ub97c \ud574\uc81c\ud558\uc138\uc694."
)
DLG_FILTER_TITLE = "\uc2e4\uc2dc\uac04 \ud544\ud130 \uc124\uc815"
DLG_FILTER_HINT = (
    "\uae30\ubcf8: \uc870\uac74\uc2dd\uc5d0 \uac78\ub9b0 \uc885\ubaa9\uc740 \ubaa8\ub450 \ud45c\uc2dc\ub429\ub2c8\ub2e4 (\ub0a9\ud488\ucc98\uba85=\uc2e4\uc81c \uc885\ubaa9\uba85).\n"
    "\uc9c4\ud589\uc644\ub8cc \uc5f4\uc5d0 \uc870\uac74\ud1b5\uacfc/\uc218\uc2e0\uc911/\ubbf8\ub2ec\uc744 \ud45c\uc2dc\ud569\ub2c8\ub2e4.\n\n"
    "\uc601\uc5c5\ub9e4\ucd9c(\ud1b5\ud569\uc794\ub7c9): \ub9e4\ub3c4\ucd1d\uc794\ub7c9 / (\ub9e4\ub3c4+\ub9e4\uc218) \ube44\uc728\n"
    "\uccb4\uacb0\uac15\ub3c4: \ud0a4\uc6c0 \uccb4\uacb0\uac15\ub3c4 \uc2e4\uc2dc\uac04 \uac12"
)
LBL_SELL_PCT = "\ub9e4\ub3c4\uc794\ub7c9 \ube44\uc728 (\ucd5c\uc18c)"
LBL_EXEC_STRENGTH = "\uccb4\uacb0\uac15\ub3c4 (\ucd5c\uc18c)"
LBL_PASS_ONLY = "\ud544\ud130 \ud1b5\uacfc \uc885\ubaa9\ub9cc \ud45c\uc2dc"
MSG_FILTER_APPLIED = (
    "\uc870\uac74\uc2dd {cond}\uac74  |  \ud45c\uc2dc {count}\uac74  |  "
    "\ud544\ud130\ud1b5\uacfc {passed_count}\uac74  |  \ub9e4\ub3c4\uc794\ub7c9 {sell_pct:.0f}% \u2191  "
    "\uccb4\uacb0 {strength:.0f} \u2191"
)
MSG_COND_COUNT = "\uc870\uac74\uc2dd \uac80\uc0c9: {count}\uac1c \uc885\ubaa9 (\uc2e4\uc2dc\uac04 \ud3b8\uc785 \uc911...)"
MSG_WATCH_COUNT = (
    "\uad00\uc2ec\uc885\ubaa9 {count}\uac1c \ud45c\uc2dc (\uc870\uac74\uc2dd \uc5c6\uc774 \uc9c4\ud589, config watch_codes)"
)
MSG_MARKET_COUNT = (
    "\ucf54\uc2a4\ud53c\u00b7\ucf54\uc2a4\ub2e5 {count}\uac1c \uc885\ubaa9 \ub85c\ub4dc \uc911 "
    "(\uc2e4\uc2dc\uac04 \uc2dc\uc138 \uc218\uc2e0 \uc911...)"
)
MSG_COND_REFRESH = "\uc870\uac74\uc2dd \uc7ac\uc870\ud68c: {added}\uac1c \ucd94\uac00 (\uc804\uccb4 {total}\uac1c)"
MSG_COND_ZERO = (
    "\uac80\uc0c9 \uc885\ubaa9\uc774 0\uac74\uc785\ub2c8\ub2e4.\n"
    "F5\ub85c \uc7ac\uc5f0\ub3d9 \ud6c4 \uc870\uac74\uc2dd \uc120\ud0dd, \ub610\ub294 config.yaml watch_codes\ub97c \ud655\uc778\ud558\uc138\uc694."
)
NOTE_MATCH = "\uc870\uac74\ud1b5\uacfc"
NOTE_WAIT = "\uc218\uc2e0\uc911"
NOTE_FAIL = "\ubbf8\ub2ec"
NOTE_LOADING = "\uc870\ud68c\uc911"
DLG_COND_TITLE = "\uc870\uac74\uc2dd \uc120\ud0dd"
DLG_COND_HINT = (
    "\uc601\uc6a9\ubb38\uc5d0 \uc800\uc7a5\ud55c \uc870\uac74\uc2dd \ubaa9\ub85d\uc785\ub2c8\ub2e4.\n"
    "Ctrl+\ud074\ub9ad\uc73c\ub85c \uc5ec\ub7ec \uac1c \uc120\ud0dd \uac00\ub2a5\ud569\ub2c8\ub2e4."
)
DLG_COND_OK = "\uc120\ud0dd \uc801\uc6a9"
DLG_COND_SKIP = "\uc870\uac74 \uc5c6\uc774 \uc9c4\ud589"
DLG_COND_EMPTY = "\uc870\uac74\uc2dd\uc744 \ud558\ub098 \uc774\uc0c1 \uc120\ud0dd\ud558\uc138\uc694."
DLG_COND_NONE = "\uc800\uc7a5\ub41c \uc870\uac74\uc2dd\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.\n\uc601\uc6a9\ubb38\uc5d0\uc11c \uc870\uac74\uc2dd\uc744 \uba3c\uc800 \ub9cc\ub4dc\uc138\uc694."
DLG_COND_LOAD_FAIL = "\uc870\uac74\uc2dd \ubaa9\ub85d \uc870\ud68c \uc2e4\ud328:\n{err}"
STATUS_FMT = (
    "\uc900\ube44  |  \uc7ac\uace0\ud604\ud669  |  "
    "\ub9c8\uc9c0\ub9c9 \uc800\uc7a5: \uc624\ub298 {t}  |  ERP\uc5f0\ub3d9: {sync}  |  100%"
)

MSG_ERP_TITLE = "ERP \uc6d0\uaca9 \uc5f0\ub3d9"
MSG_ERP_BODY = (
    "\uc0ac\ub0b4 \uc7ac\uace0 \uc11c\ubc84\uc5d0 \uc5f0\uacb0\ud569\ub2c8\ub2e4.\n"
    "\uc778\uc99d \ucc3d\uc5d0\uc11c \ubaa8\uc758\ud22c\uc790(\ucea0\uce58\ubaa8\uc758) \uc120\ud0dd \ud6c4 \ub85c\uadf8\uc778\ud558\uc138\uc694."
)
MSG_CONN_FAIL = (
    "\uc11c\ubc84 \uc5f0\uacb0\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.\n\n"
    "opstarter \uacbd\uace0\uac00 \ub610 \ub744\uc6b4 \uacbd\uc6b0:\n"
    "1) \uc774 \ucc3d\uc744 \ub2eb\uace0 C:\\OpenAPI\\force_close_kiwoom.bat\n"
    "2) \ud0a4\uc6c0_\ud55c\ubc88\uc5d0_\uc815\ub9ac.bat \uc2e4\ud589\n"
    "3) \uc644\ub8cc \ud6c4 \uc7ac\uc2e4\ud589, F5\ub85c \uc5f0\ub3d9"
)
MSG_CONN_FAIL_FMT = "\uc11c\ubc84 \uc5f0\uacb0\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.\n\n{detail}"
MSG_FIRST_RUN = (
    "\ucc98\uc74c \uc0ac\uc6a9 \uc804 \ud0a4\uc6c0_\ud55c\ubc88\uc5d0_\uc815\ub9ac.bat\ub97c\n"
    "\ud55c \ubc88 \uc2e4\ud589\ud574 \uc8fc\uc138\uc694.\n"
    "(\uc774\ud6c4\uc5d0\ub294 \uc7ac\uace0\uc2e4\uc801_\uc9d1\uacc4.bat \ubc14\ub85c \uac00\ub2a5)"
)
MSG_NOT_MOCK = "\ubaa8\uc758 \uc11c\ubc84\uac00 \uc544\ub2d9\ub2c8\ub2e4. \ucea0\uce58\ubaa8\uc758 \uc811\uc18d\uc744 \ud655\uc778\ud558\uc138\uc694."
MSG_LINK_OK = "ERP \uc7ac\uace0 \ub370\uc774\ud130 \uc5f0\ub3d9 \uc644\ub8cc"
MSG_BRIDGE_LINK_OK = "ERP \uc6d0\uaca9 \uc5f0\ub3d9 \uc644\ub8cc (\ube0c\ub9bf\uc9c0 \uc11c\ubc84)"
MSG_BRIDGE_CONN_FAIL = (
    "\ube0c\ub9bf\uc9c0 \uc11c\ubc84\uc5d0 \uc5f0\uacb0\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.\n\n"
    "1) \ud638\uc2a4\ud2b8 PC: \ube0c\ub9bf\uc9c0-\ucf1c\uae30.bat \uc2e4\ud589 \uc911\n"
    "2) \ud638\uc2a4\ud2b8 PC: \ud0a4\uc6c0 \ubaa8\uc758\ud22c\uc790 \ub85c\uadf8\uc778 \uc644\ub8cc\n"
    "3) \uace0\uac1d PC: ping \ud638\uc2a4\ud2b8IP (\uac19\uc740 Wi-Fi)\n"
    "4) \ud638\uc2a4\ud2b8: \ube0c\ub9bf\uc9c0-\ubc29\ud654\ubcbd\uc5f4\uae30.bat"
)
MSG_BRIDGE_HOST_EMPTY = "config.yaml bridge.host \ub610\ub294 \uc2e4\ud589 \uc2dc IP\ub97c \uc785\ub825\ud558\uc138\uc694."
MSG_BRIDGE_CLIENT_HINT = (
    "\uc6d0\uaca9 ERP \ubaa8\ub4dc\uc785\ub2c8\ub2e4.\n"
    "\ud638\uc2a4\ud2b8 PC\uc5d0\uc11c \ud0a4\uc6c0 \ub85c\uadf8\uc778\uc774 \uc644\ub8cc\ub41c \uc0c1\ud0dc\uc5ec\uc57c \ud569\ub2c8\ub2e4."
)
BTN_CANCEL = "\ucde8\uc18c"
PROGRESS_BRIDGE_CONNECT = "\ud638\uc2a4\ud2b8 \ube0c\ub9bf\uc9c0 \uc5f0\uacb0 \uc911..."
PROGRESS_LOAD_DATA = "\uc885\ubaa9 \ub370\uc774\ud130 \ubd88\ub7ec\uc624\ub294 \uc911..."
BRIDGE_TICK_KIWOOM_OK = "\ud0a4\uc6c0 \uc5f0\uacb0 \ud655\uc778\ub428"
BRIDGE_TICK_HOST_OK = (
    "\ud638\uc2a4\ud2b8 \uc751\ub2f5 OK \u2014 \ud0a4\uc6c0 \ub85c\uadf8\uc778 \ub300\uae30 \uc911...\n"
    "({host}:{port})"
)
BRIDGE_TICK_CONNECTING = (
    "\ube0c\ub9bf\uc9c0 \uc5f0\uacb0 \uc2dc\ub3c4 \uc911...\n"
    "ping {host} / \ubc29\ud654\ubcbd 8766 \ud655\uc778"
)
BRIDGE_TICK_NO_KIWOOM = (
    "\ud638\uc2a4\ud2b8\ub294 \uc751\ub2f5\ud588\uc73c\ub098 \ud0a4\uc6c0\uc774 \uc544\uc9c1 \ub85c\uadf8\uc778\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4."
)
REMOTE_SPLASH_TITLE = "ERP \uc6d0\uaca9 UI"
REMOTE_SPLASH_START = "\uc2dc\uc791 \uc911..."
REMOTE_PREPARE = "ERP \uc6d0\uaca9 UI \uc900\ub9ac \uc911..."
REMOTE_CONFIG_READ = "\uc124\uc815 \uc77d\ub294 \uc911..."
REMOTE_OPEN_UI = "ERP \ud654\uba74\uc744 \uc5ec\ub294 \uc911..."
REMOTE_HOST_FMT = "\ud638\uc2a4\ud2b8: {host}\n\n"
REMOTE_SYNC_CONNECT_FMT = "\ud638\uc2a4\ud2b8 \uc5f0\uacb0 \uc911...\n{url}"
REMOTE_SYNC_FAIL_FMT = (
    "\ub3d9\uae30\ud654 \uc2e4\ud328 (\ud638\uc2a4\ud2b8 \uc5f0\uacb0): {exc}\n\n"
    "F5\ub85c \uc5f0\uacb0\uc740 \uc2dc\ub3c4\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4."
)
REMOTE_SYNC_UPDATE_FMT = "\uc5c5\ub370\uc774\ud2b8 {count}\uac1c \ud30c\uc77c \uc801\uc6a9 (v{version})"
REMOTE_SYNC_LATEST_FMT = "\ucd5c\uc2e0 \ubc84\uc804\uc785\ub2c8\ub2e4 (v{version})"
REMOTE_SYNC_DOWNLOAD_FMT = "\ub2e4\uc6b4\ub85c\ub4dc: {rel}"
REMOTE_BRIDGE_IP_PROMPT = "\ube0c\ub9bf\uc9c0 \uc11c\ubc84 IP (\ud638\uc2a4\ud2b8 PC):"
REMOTE_HOST_CONFIG_WARN = "config.yaml \uc758 bridge.host \uc5d0 \ud638\uc2a4\ud2b8 IP\ub97c \ub123\uc5b4 \uc8fc\uc138\uc694."
REMOTE_FATAL_TITLE = "ERP \uc6d0\uaca9 UI \uc624\ub958"
REMOTE_ENTER_CLOSE = "Enter \ud0a4\ub97c \ub20c\ub7ec \uc885\ub8cc..."
MSG_REFRESH_OK = "\ub370\uc774\ud130 \uc0c8\ub85c\uace0\uce68 \uc644\ub8cc"
MSG_SAVE_OK = "\uc800\uc7a5 \uc644\ub8cc"

NOTE_OK = "\uc815\uc0c1"
NOTE_HOLD_FMT = "\ubcf4\uc720({pnl:+.1f}%)"
SELL_PCT_FMT = "{pct:.1f}% ({sell:,}/{total:,})"

MOCK_LOGIN_HINT = (
    "\ud0a4\uc6c0 \ub85c\uadf8\uc778 \ucc3d\uc5d0\uc11c\n"
    "\u2611 \ubaa8\uc758\ud22c\uc790 \uc811\uc18d\n"
    "\u2611 \ucea0\uce58\ubaa8\uc758 (\ud45c\uc2dc\ub418\ub294 \uacbd\uc6b0)\n"
    "\uc744 \uc120\ud0dd\ud55c \ub4a4 \ub85c\uadf8\uc778\ud558\uc138\uc694."
)

F_STOCK_CODE = "\uc885\ubaa9\ucf54\ub4dc"
F_CURRENT_PRICE = "\ud604\uc7ac\uac00"
F_REF_PRICE = "\uae30\uc900\uac00"
F_STOCK_NAME = "\uc885\ubaa9\uba85"
RQ_REF = "\uae30\uc900\uac00\uc870\ud68c"
RQ_HOGA = "\ud638\uac00\uc870\ud68c"
F_SELL_TOTAL = "\ub9e4\ub3c4\ud638\uac00\ucd1d\uc794\ub7c9"
F_BUY_TOTAL = "\ub9e4\uc218\ud638\uac00\ucd1d\uc794\ub7c9"
REAL_TICK = "\uc8fc\uc2dd\uccb4\uacb0"
REAL_HOGA = "\uc8fc\uc2dd\ud638\uac00\uc794\ub7c9"
FILL_DONE = "\uccb4\uacb0"
