import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtWebEngine

ApplicationWindow {
    id: root
    width: 1280
    height: 820
    visible: true
    title: "Darkelf Shadow"
    color: "#0a0b10"

    // ---- design tokens ----
    readonly property color accent: darkelf.accentColor
    readonly property color accentSoft: Qt.rgba(accent.r, accent.g, accent.b, 0.14)
    readonly property color bg:       "#0a0b10"
    readonly property color panel:    "#0d0f15"
    readonly property color panel2:   "#13151f"
    readonly property color card:     "#161922"
    readonly property color stroke:   "#1f2330"
    readonly property color textCol:  "#e9edf4"
    readonly property color muted:    "#8b93a3"
    readonly property color good:     "#34d399"
    readonly property color warn:     "#fbbf24"
    readonly property color bad:      "#f87171"

    // ---- app state ----
    property bool jsEnabled: true
    property bool showBookmarksBar: true
    property var    bookmarks: []
    property var    aiStats: ({})
    property string activeUrl: ""
    property string activeTitle: ""
    property int    bmTick: 0
    readonly property bool curBookmarked: { bmTick; return darkelf.isBookmarked(activeUrl) }
    readonly property bool onHome: activeUrl.indexOf("darkelf.home") >= 0 || activeUrl === ""

    function reloadBookmarks() { bookmarks = darkelf.getBookmarks(); bmTick++ }
    function refreshActive() {
        var t = stack.itemAt(stack.currentIndex)
        var u = (t && t.web) ? t.web.url.toString() : ""
        activeUrl = u
        activeTitle = (t && t.web) ? t.web.title : ""
        addr.text = (u.indexOf("darkelf.home") >= 0) ? "" : u
    }
    function activeWeb() {
        var t = stack.itemAt(stack.currentIndex)
        return t ? t.web : null
    }
    function addTab(url) {
        tabsModel.append({ "initialUrl": url || "", "title": "New Tab", "pageUrl": "" })
        stack.currentIndex = tabsModel.count - 1
        addr.forceActiveFocus()
        addr.selectAll()
    }
    function openLink(url) { addTab(url); settingsPage.close() }
    function closeTab(i) {
        if (tabsModel.count <= 1) {
            tabsModel.setProperty(0, "initialUrl", "")
            var t0 = stack.itemAt(0)
            if (t0 && t0.web) t0.web.loadHtml(darkelf.homepageHtml, "https://darkelf.home/")
            return
        }
        tabsModel.remove(i)
        if (stack.currentIndex >= tabsModel.count) stack.currentIndex = tabsModel.count - 1
    }
    function goHome() { var w = activeWeb(); if (w) w.loadHtml(darkelf.homepageHtml, "https://darkelf.home/") }
    function navigate() {
        var w = activeWeb()
        if (!w) return
        var resolved = darkelf.resolveInput(addr.text)
        if (resolved === "") goHome(); else w.url = resolved
    }
    function zoomBy(d) { var w = activeWeb(); if (w) w.zoomFactor = Math.min(3.0, Math.max(0.3, w.zoomFactor + d)) }
    function zoomReset() { var w = activeWeb(); if (w) w.zoomFactor = 1.0 }
    function doFind(t, forward) { var w = activeWeb(); if (w) w.findText(t, forward ? 0 : WebEngineView.FindBackward) }
    function toggleDevtools() { var t = stack.itemAt(stack.currentIndex); if (t) t.devtoolsOpen = !t.devtoolsOpen }
    function openReport() { aiStats = darkelf.miniaiStats(); aiPopup.open() }

    Connections {
        target: darkelf
        function onQuitRequested() { Qt.quit() }
        function onBookmarksChanged() { root.reloadBookmarks() }
        function onHomepageHtmlChanged() {
            if (root.onHome) { var w = root.activeWeb(); if (w) w.loadHtml(darkelf.homepageHtml, "https://darkelf.home/") }
        }
    }

    FileDialog {
        id: bgFileDialog
        title: "Choose a background image"
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp)"]
        onAccepted: darkelf.importBackgroundFile(selectedFile)
    }

    // ===================== shortcuts =====================
    Shortcut { sequence: "Ctrl+T"; onActivated: root.addTab("") }
    Shortcut { sequence: "Ctrl+W"; onActivated: root.closeTab(stack.currentIndex) }
    Shortcut { sequence: "Ctrl+L"; onActivated: { addr.forceActiveFocus(); addr.selectAll() } }
    Shortcut { sequence: "Ctrl+R"; onActivated: { var w = root.activeWeb(); if (w) w.reload() } }
    Shortcut { sequence: "F5";     onActivated: { var w = root.activeWeb(); if (w) w.reload() } }
    Shortcut { sequence: "Alt+Left";  onActivated: { var w = root.activeWeb(); if (w) w.goBack() } }
    Shortcut { sequence: "Alt+Right"; onActivated: { var w = root.activeWeb(); if (w) w.goForward() } }
    Shortcut { sequence: "F12"; onActivated: root.toggleDevtools() }
    Shortcut { sequence: "Ctrl+,"; onActivated: { settingsPage.section = 0; settingsPage.open() } }
    Shortcut { sequence: "Ctrl+D"; onActivated: { if (!root.onHome) darkelf.toggleBookmark(root.activeTitle, root.activeUrl) } }
    Shortcut { sequence: "Ctrl+F"; onActivated: findBar.show() }
    Shortcut { sequence: "Ctrl+="; onActivated: root.zoomBy(0.1) }
    Shortcut { sequence: "Ctrl++"; onActivated: root.zoomBy(0.1) }
    Shortcut { sequence: "Ctrl+-"; onActivated: root.zoomBy(-0.1) }
    Shortcut { sequence: "Ctrl+0"; onActivated: root.zoomReset() }

    // ===================== layout =====================
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // -------- toolbar --------
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 52
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#10131c" }
                GradientStop { position: 1.0; color: root.panel }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: root.stroke }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 4

                NavButton { glyph: "‹"; tip: "Back";    onClicked: { var w = root.activeWeb(); if (w) w.goBack() } }
                NavButton { glyph: "›"; tip: "Forward"; onClicked: { var w = root.activeWeb(); if (w) w.goForward() } }
                NavButton { glyph: "↻"; tip: "Reload";  onClicked: { var w = root.activeWeb(); if (w) w.reload() } }
                NavButton { glyph: "⌂"; tip: "Home";    onClicked: root.goHome() }

                // omnibox
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    radius: 19
                    color: addr.activeFocus ? root.panel2 : "#0f121a"
                    border.color: addr.activeFocus ? root.accent : root.stroke
                    border.width: addr.activeFocus ? 2 : 1
                    Behavior on color { ColorAnimation { duration: 140 } }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 15
                        anchors.rightMargin: 8
                        spacing: 8
                        Text {
                            text: (root.activeUrl.indexOf("https") === 0) ? "🔒" : (root.onHome ? "🛡" : "⚠")
                            color: root.muted; font.pixelSize: 13
                        }
                        TextField {
                            id: addr
                            Layout.fillWidth: true
                            color: root.textCol
                            font.pixelSize: 14
                            selectByMouse: true
                            placeholderText: "Search DuckDuckGo or enter address"
                            placeholderTextColor: root.muted
                            background: Item {}
                            onAccepted: root.navigate()
                        }
                        ToolButton {
                            visible: !root.onHome
                            width: 28; height: 28
                            ToolTip.visible: hovered
                            ToolTip.text: root.curBookmarked ? "Remove bookmark" : "Bookmark this page (Ctrl+D)"
                            contentItem: Text {
                                text: root.curBookmarked ? "★" : "☆"
                                color: root.curBookmarked ? root.accent : root.muted
                                font.pixelSize: 18
                                horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                                Behavior on color { ColorAnimation { duration: 120 } }
                            }
                            background: Rectangle { radius: 7; color: parent.hovered ? root.card : "transparent"; Behavior on color { ColorAnimation { duration: 120 } } }
                            onClicked: darkelf.toggleBookmark(root.activeTitle, root.activeUrl)
                        }
                    }
                }

                // status cluster
                Rectangle {
                    Layout.preferredHeight: 42
                    Layout.leftMargin: 4
                    implicitWidth: clusterRow.implicitWidth + 14
                    radius: 14
                    color: "#0f121a"
                    border.color: root.stroke
                    border.width: 1

                    Row {
                        id: clusterRow
                        anchors.centerIn: parent
                        spacing: 2

                        ToolButton {
                            id: shieldBtn
                            width: 36; height: 36
                            property string status: "STANDBY"
                            ToolTip.visible: hovered
                            ToolTip.text: "MiniAI: " + status
                            contentItem: Item {
                                Text { anchors.centerIn: parent; text: "🛡"; font.pixelSize: 16 }
                                Rectangle {
                                    visible: shieldBtn.status !== "STANDBY"
                                    width: 9; height: 9; radius: 5
                                    anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 3
                                    color: shieldBtn.status === "PANIC" ? root.bad : root.warn
                                    border.color: "#0f121a"; border.width: 1.5
                                    SequentialAnimation on opacity {
                                        running: shieldBtn.status !== "STANDBY"; loops: Animation.Infinite
                                        NumberAnimation { from: 1.0; to: 0.35; duration: 700; easing.type: Easing.InOutQuad }
                                        NumberAnimation { from: 0.35; to: 1.0; duration: 700; easing.type: Easing.InOutQuad }
                                    }
                                }
                            }
                            background: Rectangle { radius: 10; color: shieldBtn.hovered ? root.card : "transparent"; Behavior on color { ColorAnimation { duration: 120 } } }
                            onClicked: root.openReport()
                            Connections { target: darkelf; function onMiniaiStatusChanged(s) { shieldBtn.status = s } }
                        }

                        ClusterButton { glyph: "☰"; tip: "Menu"; onClicked: mainMenu.popup() }
                        ClusterButton { glyph: "☢"; tip: "Delete all data"; danger: true; onClicked: nukeConfirm.open() }
                    }
                }
            }
        }

        // -------- bookmarks bar --------
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: (root.showBookmarksBar && root.bookmarks.length > 0) ? 36 : 0
            visible: root.showBookmarksBar && root.bookmarks.length > 0
            color: root.panel
            Behavior on implicitHeight { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: root.stroke }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12; anchors.rightMargin: 8
                spacing: 6
                Text { text: "🔖"; color: root.muted; font.pixelSize: 13 }
                ListView {
                    id: bmBar
                    Layout.fillWidth: true; Layout.fillHeight: true
                    orientation: ListView.Horizontal; spacing: 4; clip: true
                    model: root.bookmarks
                    delegate: Rectangle {
                        height: 26
                        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                        width: bmLabel.implicitWidth + avatar.width + 22
                        radius: 8
                        color: bmHover.hovered ? root.card : "transparent"
                        Behavior on color { ColorAnimation { duration: 120 } }
                        Row {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left; anchors.leftMargin: 7; spacing: 6
                            Rectangle {
                                id: avatar
                                width: 15; height: 15; radius: 4
                                anchors.verticalCenter: parent.verticalCenter
                                color: root.accent
                                Text { anchors.centerIn: parent; text: (modelData.title || "?").charAt(0).toUpperCase(); color: "#0a0b10"; font.pixelSize: 9; font.bold: true }
                            }
                            Text {
                                id: bmLabel
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.title || modelData.url
                                color: root.textCol; font.pixelSize: 12
                                elide: Text.ElideRight; maximumLineCount: 1
                            }
                        }
                        HoverHandler { id: bmHover }
                        TapHandler {
                            acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                            onTapped: function(pt, btn) {
                                if (btn === Qt.MiddleButton) darkelf.removeBookmark(modelData.url)
                                else { var w = root.activeWeb(); if (w) w.url = modelData.url }
                            }
                        }
                        ToolTip.visible: bmHover.hovered
                        ToolTip.text: modelData.url + "\n(middle-click to remove)"
                    }
                }
            }
        }

        // -------- tab strip --------
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 38
            color: root.bg
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                spacing: 4
                ListView {
                    id: tabBar
                    Layout.fillWidth: true; Layout.fillHeight: true
                    orientation: ListView.Horizontal; spacing: 5; clip: true
                    model: tabsModel
                    delegate: Rectangle {
                        height: 30
                        width: Math.min(220, Math.max(130, titleText.implicitWidth + 46))
                        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                        radius: 10
                        color: index === stack.currentIndex ? root.accent : root.panel2
                        Behavior on color { ColorAnimation { duration: 140 } }
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12; anchors.rightMargin: 6
                            spacing: 6
                            Text {
                                id: titleText
                                Layout.fillWidth: true
                                text: model.title && model.title.length ? model.title : "New Tab"
                                elide: Text.ElideRight
                                color: index === stack.currentIndex ? "#0a0b10" : root.textCol
                                font.pixelSize: 12
                                font.weight: index === stack.currentIndex ? Font.DemiBold : Font.Normal
                            }
                            Text {
                                text: "×"
                                color: index === stack.currentIndex ? "#0a0b10" : root.muted
                                font.pixelSize: 16
                                MouseArea { anchors.fill: parent; anchors.margins: -4; onClicked: root.closeTab(index) }
                            }
                        }
                        MouseArea { anchors.fill: parent; z: -1; onClicked: stack.currentIndex = index }
                    }
                }
                NavButton { glyph: "+"; tip: "New tab"; onClicked: root.addTab("") }
            }
        }

        // -------- find bar --------
        Rectangle {
            id: findBar
            property bool active: false
            function show() { active = true; findInput.forceActiveFocus(); findInput.selectAll() }
            function hide() { active = false; root.doFind("", true) }
            Layout.fillWidth: true
            implicitHeight: active ? 46 : 0
            visible: active
            color: root.panel2
            Behavior on implicitHeight { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: root.stroke }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14; anchors.rightMargin: 8
                spacing: 8
                Text { text: "Find"; color: root.muted; font.pixelSize: 13 }
                TextField {
                    id: findInput
                    Layout.preferredWidth: 340
                    color: root.textCol
                    background: Rectangle { color: root.card; radius: 8; border.color: root.stroke }
                    onTextChanged: root.doFind(text, true)
                    onAccepted: root.doFind(text, true)
                    Keys.onEscapePressed: findBar.hide()
                }
                NavButton { glyph: "‹"; tip: "Previous"; onClicked: root.doFind(findInput.text, false) }
                NavButton { glyph: "›"; tip: "Next"; onClicked: root.doFind(findInput.text, true) }
                Item { Layout.fillWidth: true }
                NavButton { glyph: "×"; tip: "Close"; onClicked: findBar.hide() }
            }
        }

        // -------- web stack --------
        StackLayout {
            id: stack
            Layout.fillWidth: true; Layout.fillHeight: true
            currentIndex: 0
            onCurrentIndexChanged: root.refreshActive()
            Repeater {
                model: tabsModel
                delegate: Item {
                    id: tabItem
                    property alias web: webview
                    property bool devtoolsOpen: false
                    SplitView {
                        anchors.fill: parent
                        orientation: Qt.Vertical
                        WebEngineView {
                            id: webview
                            SplitView.fillWidth: true; SplitView.fillHeight: true
                            profile: darkelfProfile
                            settings.javascriptEnabled: root.jsEnabled
                            settings.fullScreenSupportEnabled: true
                            Component.onCompleted: {
                                if (model.initialUrl && model.initialUrl.length) url = model.initialUrl
                                else loadHtml(darkelf.homepageHtml, "https://darkelf.home/")
                            }
                            onTitleChanged: {
                                tabsModel.setProperty(index, "title", title)
                                if (index === stack.currentIndex) root.activeTitle = title
                            }
                            onUrlChanged: {
                                tabsModel.setProperty(index, "pageUrl", url.toString())
                                if (index === stack.currentIndex) root.refreshActive()
                            }
                            onLoadingChanged: function(req) {
                                if (req.status === WebEngineView.LoadSucceededStatus) {
                                    var host = ""
                                    try { host = (new URL(url.toString())).hostname } catch(e) {}
                                    var css = host ? darkelf.cssForHost(host) : ""
                                    if (css && css.length) {
                                        var js = "(function(){try{var s=document.createElement('style');s.textContent=" +
                                                 JSON.stringify(css) + ";(document.head||document.documentElement).appendChild(s);}catch(e){}})();"
                                        runJavaScript(js)
                                    }
                                }
                            }
                            onNewWindowRequested: function(req) { root.addTab(req.requestedUrl.toString()) }
                            onFullScreenRequested: function(req) { req.accept() }
                        }
                        WebEngineView {
                            id: devview
                            visible: tabItem.devtoolsOpen
                            SplitView.preferredHeight: tabItem.devtoolsOpen ? root.height * 0.4 : 0
                            SplitView.minimumHeight: tabItem.devtoolsOpen ? 120 : 0
                            profile: darkelfProfile
                            Component.onCompleted: inspectedView = webview
                        }
                    }
                }
            }
        }
    }

    // ===================== reusable components =====================
    component NavButton: ToolButton {
        property string glyph: ""
        property string tip: ""
        property bool danger: false
        implicitWidth: 38; implicitHeight: 38
        ToolTip.visible: hovered && tip.length > 0
        ToolTip.text: tip
        contentItem: Text {
            text: glyph
            color: danger ? root.bad : root.textCol
            font.pixelSize: 19
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 11
            color: parent.hovered ? (danger ? "#2a1416" : root.panel2) : "transparent"
            Behavior on color { ColorAnimation { duration: 130 } }
        }
    }

    component ClusterButton: ToolButton {
        property string glyph: ""
        property string tip: ""
        property bool danger: false
        width: 36; height: 36
        ToolTip.visible: hovered && tip.length > 0
        ToolTip.text: tip
        contentItem: Text {
            text: glyph
            color: danger ? root.bad : root.textCol
            font.pixelSize: 16
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 10
            color: parent.hovered ? (danger ? "#2a1416" : root.card) : "transparent"
            Behavior on color { ColorAnimation { duration: 130 } }
        }
    }

    // unified button — `accent` (filled) or ghost (outlined)
    component DButton: Button {
        property bool accent: false
        property bool danger: false
        implicitHeight: 36
        leftPadding: 18; rightPadding: 18
        contentItem: Text {
            text: parent.text
            color: parent.accent ? "#0a0b10" : (parent.danger ? root.bad : root.textCol)
            font.pixelSize: 13; font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 10
            color: parent.accent
                   ? (parent.down ? Qt.darker(root.accent, 1.1) : root.accent)
                   : (parent.hovered ? root.card : root.panel2)
            border.color: parent.accent ? "transparent" : root.stroke
            border.width: 1
            Behavior on color { ColorAnimation { duration: 130 } }
        }
    }

    component DMenuItem: MenuItem {
        id: mi
        property string accel: ""
        implicitHeight: 38; implicitWidth: 272
        contentItem: Item {
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left; anchors.leftMargin: 14
                text: mi.text; color: mi.highlighted ? "#0a0b10" : root.textCol; font.pixelSize: 13
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right; anchors.rightMargin: 14
                text: mi.accel; color: mi.highlighted ? "#0a0b10" : root.muted; font.pixelSize: 11
            }
        }
        background: Rectangle { radius: 7; color: mi.highlighted ? root.accent : "transparent"; Behavior on color { ColorAnimation { duration: 90 } } }
    }

    // fluid modal popup base (dim + scale/fade)
    component FluidPopup: Popup {
        modal: true
        anchors.centerIn: Overlay.overlay
        padding: 0
        Overlay.modal: Rectangle { color: "#aa05060a" }
        background: Rectangle { color: root.panel; radius: 18; border.color: root.stroke; border.width: 1 }
        enter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 170; easing.type: Easing.OutCubic }
                NumberAnimation { property: "scale"; from: 0.95; to: 1.0; duration: 220; easing.type: Easing.OutCubic }
            }
        }
        exit: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 130 }
                NumberAnimation { property: "scale"; from: 1.0; to: 0.97; duration: 130 }
            }
        }
    }

    // dashboard primitives
    component StatCard: Rectangle {
        property string value: ""
        property string label: ""
        Layout.fillWidth: true
        implicitHeight: 78
        radius: 14
        color: root.card
        border.color: root.stroke
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 14; spacing: 2
            Text { text: value; color: root.accent; font.pixelSize: 26; font.bold: true }
            Text { text: label; color: root.muted; font.pixelSize: 11; font.letterSpacing: 0.5 }
        }
    }

    component MetricCard: Rectangle {
        property string label: ""
        property int value: 0
        property color tone: root.textCol
        Layout.fillWidth: true
        implicitHeight: 62
        radius: 12
        color: root.card
        border.color: root.stroke
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14
            Text { text: label; color: root.muted; font.pixelSize: 12; Layout.fillWidth: true }
            Text { text: value; color: value > 0 ? tone : root.muted; font.pixelSize: 20; font.bold: true }
        }
    }

    component DefenseBadge: Rectangle {
        property string label: ""
        property string action: ""
        Layout.fillWidth: true
        implicitHeight: 40
        radius: 10
        color: "#10141d"
        border.color: root.stroke
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 8
            Rectangle { width: 7; height: 7; radius: 4; color: root.good }
            Text { text: label; color: root.textCol; font.pixelSize: 12; Layout.fillWidth: true }
            Text { text: action; color: root.good; font.pixelSize: 10; font.weight: Font.DemiBold }
        }
    }

    component LinkChip: Rectangle {
        property string label: ""
        property string url: ""
        implicitWidth: lc.implicitWidth + 30
        implicitHeight: 34
        radius: 10
        color: lch.hovered ? root.accentSoft : root.card
        border.color: lch.hovered ? root.accent : root.stroke
        Behavior on color { ColorAnimation { duration: 130 } }
        Row {
            anchors.centerIn: parent; spacing: 7
            Text { text: "↗"; color: root.accent; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
            Text { id: lc; text: label; color: root.textCol; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
        }
        HoverHandler { id: lch; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: root.openLink(url) }
    }

    component FeatureChip: Rectangle {
        property string label: ""
        implicitWidth: fc.implicitWidth + 26
        implicitHeight: 30
        radius: 15
        color: root.accentSoft
        border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.4)
        Text { id: fc; anchors.centerIn: parent; text: label; color: root.textCol; font.pixelSize: 11 }
    }

    component BgSwatch: Rectangle {
        property string bid: ""
        property string label: ""
        property color c1: "#13151f"
        property color c2: "#05060a"
        width: 108; height: 66; radius: 11
        border.width: darkelf.backgroundChoice === bid ? 3 : 1
        border.color: darkelf.backgroundChoice === bid ? root.accent : root.stroke
        gradient: Gradient {
            GradientStop { position: 0.0; color: c1 }
            GradientStop { position: 1.0; color: c2 }
        }
        scale: bgHover.hovered ? 1.04 : 1.0
        Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
        Text {
            anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottomMargin: 6
            text: label; color: "#e9edf4"; font.pixelSize: 10; font.weight: Font.DemiBold
            style: Text.Outline; styleColor: "#000000"
        }
        HoverHandler { id: bgHover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: darkelf.setBackground(bid) }
    }

    // ===================== hamburger menu =====================
    Menu {
        id: mainMenu
        width: 272
        padding: 6
        background: Rectangle { color: root.panel; border.color: root.stroke; radius: 12 }
        DMenuItem { text: "New Tab"; accel: "Ctrl+T"; onTriggered: root.addTab("") }
        DMenuItem { text: "Bookmark this page"; accel: "Ctrl+D"; enabled: !root.onHome; onTriggered: darkelf.toggleBookmark(root.activeTitle, root.activeUrl) }
        DMenuItem { text: root.showBookmarksBar ? "Hide bookmarks bar" : "Show bookmarks bar"; onTriggered: root.showBookmarksBar = !root.showBookmarksBar }
        MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: root.stroke } }
        DMenuItem { text: "Find on page…"; accel: "Ctrl+F"; onTriggered: findBar.show() }
        DMenuItem { text: "Zoom In"; accel: "Ctrl++"; onTriggered: root.zoomBy(0.1) }
        DMenuItem { text: "Zoom Out"; accel: "Ctrl+-"; onTriggered: root.zoomBy(-0.1) }
        DMenuItem { text: "Reset Zoom"; accel: "Ctrl+0"; onTriggered: root.zoomReset() }
        DMenuItem { text: "Developer Tools"; accel: "F12"; onTriggered: root.toggleDevtools() }
        MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: root.stroke } }
        DMenuItem { text: "Security Report"; onTriggered: root.openReport() }
        DMenuItem { text: "Bookmarks Manager"; onTriggered: { settingsPage.section = 2; settingsPage.open() } }
        DMenuItem { text: "Delete browsing data"; accel: "Ctrl+Shift+Del"; onTriggered: nukeConfirm.open() }
        DMenuItem { text: "Settings"; accel: "Ctrl+,"; onTriggered: { settingsPage.section = 0; settingsPage.open() } }
        DMenuItem { text: "About Darkelf"; onTriggered: { settingsPage.section = 3; settingsPage.open() } }
        MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: root.stroke } }
        DMenuItem { text: "Exit"; onTriggered: Qt.quit() }
    }

    // ===================== MiniAI dashboard =====================
    FluidPopup {
        id: aiPopup
        width: Math.min(760, root.width - 80)
        height: Math.min(660, root.height - 80)

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 16

            // header
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    width: 40; height: 40; radius: 12; color: root.accentSoft
                    Text { anchors.centerIn: parent; text: "🛡"; font.pixelSize: 19 }
                }
                ColumnLayout {
                    spacing: 0; Layout.fillWidth: true
                    Text { text: "MiniAI Sentinel"; color: root.textCol; font.pixelSize: 18; font.bold: true }
                    Text { text: "On-device threat monitoring"; color: root.muted; font.pixelSize: 11 }
                }
                Rectangle {
                    property string st: root.aiStats.status || "STANDBY"
                    radius: 14; implicitHeight: 28; implicitWidth: stTxt.implicitWidth + 30
                    color: st === "PANIC" ? Qt.rgba(0.97,0.44,0.44,0.16) : st === "LOCKDOWN" ? Qt.rgba(0.98,0.75,0.14,0.16) : Qt.rgba(0.2,0.83,0.6,0.16)
                    border.color: st === "PANIC" ? root.bad : st === "LOCKDOWN" ? root.warn : root.good
                    Row {
                        anchors.centerIn: parent; spacing: 7
                        Rectangle { width: 8; height: 8; radius: 4; anchors.verticalCenter: parent.verticalCenter
                                    color: parent.parent.st === "PANIC" ? root.bad : parent.parent.st === "LOCKDOWN" ? root.warn : root.good }
                        Text { id: stTxt; text: parent.parent.st; color: parent.parent.st === "PANIC" ? root.bad : parent.parent.st === "LOCKDOWN" ? root.warn : root.good
                               font.pixelSize: 12; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }

            // stat cards
            GridLayout {
                Layout.fillWidth: true
                columns: 4; columnSpacing: 12; rowSpacing: 12
                StatCard { value: (root.aiStats.uptimeMin !== undefined ? root.aiStats.uptimeMin : 0) + "m"; label: "UPTIME" }
                StatCard { value: "" + (root.aiStats.events || 0); label: "EVENTS" }
                StatCard { value: "" + (root.aiStats.domains || 0); label: "DOMAINS" }
                StatCard { value: "" + (root.aiStats.score || 0); label: "THREAT SCORE" }
            }

            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: aiPopup.width - 44
                    spacing: 16

                    Text { text: "THREAT ACTIVITY"; color: root.muted; font.pixelSize: 11; font.letterSpacing: 1.2 }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3; columnSpacing: 12; rowSpacing: 12
                        MetricCard { label: "Trackers"; value: (root.aiStats.threats && root.aiStats.threats.trackers) || 0; tone: root.warn }
                        MetricCard { label: "Fingerprinting"; value: (root.aiStats.threats && root.aiStats.threats.fingerprinting) || 0; tone: root.warn }
                        MetricCard { label: "Intrusions"; value: (root.aiStats.threats && root.aiStats.threats.intrusions) || 0; tone: root.bad }
                        MetricCard { label: "Malware"; value: (root.aiStats.threats && root.aiStats.threats.malware) || 0; tone: root.bad }
                        MetricCard { label: "Exploits"; value: (root.aiStats.threats && root.aiStats.threats.exploits) || 0; tone: root.bad }
                        MetricCard { label: "HTTPS upgrades"; value: (root.aiStats.threats && root.aiStats.threats.http_blocks) || 0; tone: root.good }
                    }

                    Text { text: "FINGERPRINT DEFENSE"; color: root.muted; font.pixelSize: 11; font.letterSpacing: 1.2 }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2; columnSpacing: 12; rowSpacing: 10
                        DefenseBadge { label: "Canvas"; action: "NOISE" }
                        DefenseBadge { label: "WebGL"; action: "SPOOFED" }
                        DefenseBadge { label: "AudioContext"; action: "ZEROED" }
                        DefenseBadge { label: "Fonts"; action: "HIDDEN" }
                        DefenseBadge { label: "Battery"; action: "SPOOFED" }
                        DefenseBadge { label: "Geolocation"; action: "BLOCKED" }
                        DefenseBadge { label: "Media Devices"; action: "EMPTY" }
                        DefenseBadge { label: "WebRTC"; action: "DISABLED" }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: (root.aiStats.status === "STANDBY" || !root.aiStats.status)
                          ? "✓ No fingerprint leaks. All tracker attempts defended."
                          : "⚠ Active defense engaged."
                    color: (root.aiStats.status === "STANDBY" || !root.aiStats.status) ? root.good : root.warn
                    font.pixelSize: 12
                }
                DButton { text: "Close"; onClicked: aiPopup.close() }
            }
        }
    }

    // ===================== Settings =====================
    FluidPopup {
        id: settingsPage
        width: Math.min(940, root.width - 80)
        height: Math.min(660, root.height - 80)
        property int section: 0

        RowLayout {
            anchors.fill: parent
            spacing: 0

            // sidebar
            Rectangle {
                Layout.preferredWidth: 214; Layout.fillHeight: true
                color: "#0b0d13"
                topLeftRadius: 18; bottomLeftRadius: 18
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 4
                    Text { text: "Settings"; color: root.textCol; font.pixelSize: 19; font.bold: true; Layout.bottomMargin: 12; Layout.leftMargin: 4 }
                    Repeater {
                        model: ["Appearance", "Privacy & Security", "Bookmarks", "About"]
                        delegate: Rectangle {
                            Layout.fillWidth: true; height: 42; radius: 10
                            color: settingsPage.section === index ? root.accent : (navHover.hovered ? root.panel2 : "transparent")
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 14
                                text: modelData
                                color: settingsPage.section === index ? "#0a0b10" : root.textCol
                                font.pixelSize: 13; font.weight: settingsPage.section === index ? Font.DemiBold : Font.Normal
                            }
                            HoverHandler { id: navHover }
                            TapHandler { onTapped: settingsPage.section = index }
                        }
                    }
                    Item { Layout.fillHeight: true }
                    DButton { text: "Close"; Layout.fillWidth: true; onClicked: settingsPage.close() }
                }
            }

            // content
            StackLayout {
                currentIndex: settingsPage.section
                Layout.fillWidth: true; Layout.fillHeight: true

                // ---- Appearance ----
                ScrollView {
                    contentWidth: availableWidth; clip: true
                    ColumnLayout {
                        width: settingsPage.width - 244; spacing: 14
                        Text { text: "Appearance"; color: root.textCol; font.pixelSize: 18; font.bold: true; Layout.leftMargin: 26; Layout.topMargin: 26 }
                        Text { text: "Accent color"; color: root.muted; font.pixelSize: 12; Layout.leftMargin: 26 }
                        Flow {
                            Layout.fillWidth: true; Layout.leftMargin: 26; Layout.rightMargin: 26; spacing: 10
                            Repeater {
                                model: ["#A855F7","#34C759","#40a9ff","#ff4d4f","#ffa940","#36cfc9","#f759ab","#FFD700","#7B68EE","#20B2AA"]
                                delegate: Rectangle {
                                    width: 36; height: 36; radius: 10; color: modelData
                                    border.width: darkelf.accentColor == modelData ? 3 : 0
                                    border.color: "#ffffff"
                                    scale: ah.hovered ? 1.08 : 1.0
                                    Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
                                    HoverHandler { id: ah; cursorShape: Qt.PointingHandCursor }
                                    TapHandler { onTapped: darkelf.accentColor = modelData }
                                }
                            }
                        }

                        Text { text: "New tab background"; color: root.muted; font.pixelSize: 12; Layout.leftMargin: 26; Layout.topMargin: 8 }
                        Flow {
                            Layout.fillWidth: true; Layout.leftMargin: 26; Layout.rightMargin: 26; spacing: 12
                            BgSwatch { bid: "aurora"; label: "Aurora"; c1: root.accent; c2: "#0a0b10" }
                            BgSwatch { bid: "graded"; label: "Graded"; c1: "#1a1d28"; c2: "#05060a" }
                            BgSwatch { bid: "matrix"; label: "Matrix"; c1: "#0a2a16"; c2: "#04070a" }
                            BgSwatch { bid: "circuit"; label: "Circuit"; c1: Qt.darker(root.accent, 2.2); c2: "#07080e" }
                            BgSwatch { bid: "nebula"; label: "Nebula"; c1: "#3a1d6b"; c2: "#0a1430" }
                            BgSwatch { bid: "void"; label: "Void"; c1: "#0c0e15"; c2: "#06070b" }
                            // import own image
                            Rectangle {
                                width: 108; height: 66; radius: 11
                                color: impHover.hovered ? root.card : "transparent"
                                border.width: darkelf.backgroundChoice === "custom" ? 3 : 1
                                border.color: darkelf.backgroundChoice === "custom" ? root.accent : root.stroke
                                Column {
                                    anchors.centerIn: parent; spacing: 1
                                    Text { text: "＋"; color: root.accent; font.pixelSize: 20; anchors.horizontalCenter: parent.horizontalCenter }
                                    Text { text: "Import"; color: root.muted; font.pixelSize: 10; anchors.horizontalCenter: parent.horizontalCenter }
                                }
                                HoverHandler { id: impHover; cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: bgFileDialog.open() }
                            }
                        }
                    }
                }

                // ---- Privacy & Security ----
                ScrollView {
                    contentWidth: availableWidth; clip: true
                    ColumnLayout {
                        width: settingsPage.width - 244; spacing: 6
                        Text { text: "Privacy & Security"; color: root.textCol; font.pixelSize: 18; font.bold: true; Layout.leftMargin: 26; Layout.topMargin: 26 }
                        RowLayout {
                            Layout.fillWidth: true; Layout.leftMargin: 26; Layout.rightMargin: 26; Layout.topMargin: 8
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 0
                                Text { text: "JavaScript"; color: root.textCol; font.pixelSize: 14 }
                                Text { text: "Allow sites to run scripts"; color: root.muted; font.pixelSize: 11 }
                            }
                            Switch { checked: root.jsEnabled; onToggled: root.jsEnabled = checked }
                        }
                        InfoRow { label: "Fingerprint defense"; value: "Active" }
                        InfoRow { label: "HTTPS upgrade"; value: "On" }
                        InfoRow { label: "WebRTC"; value: "Blocked" }
                        InfoRow { label: "Cookies / cache"; value: "In-memory (off-the-record)" }
                        InfoRow { label: "Tracker filtering"; value: "EasyList + uBO + heuristics" }
                        Item { height: 10; width: 1 }
                        DButton { text: "Delete browsing data"; danger: true; Layout.leftMargin: 26; onClicked: { settingsPage.close(); nukeConfirm.open() } }
                    }
                }

                // ---- Bookmarks ----
                ColumnLayout {
                    spacing: 10
                    Text { text: "Bookmarks"; color: root.textCol; font.pixelSize: 18; font.bold: true; Layout.leftMargin: 26; Layout.topMargin: 26 }
                    RowLayout {
                        Layout.leftMargin: 26; Layout.rightMargin: 26; Layout.fillWidth: true; spacing: 8
                        TextField {
                            id: bmTitle; Layout.preferredWidth: 180; placeholderText: "Title"; color: root.textCol
                            placeholderTextColor: root.muted
                            background: Rectangle { color: root.card; radius: 8; border.color: root.stroke }
                        }
                        TextField {
                            id: bmUrl; Layout.fillWidth: true; placeholderText: "https://example.com"; color: root.textCol
                            placeholderTextColor: root.muted
                            background: Rectangle { color: root.card; radius: 8; border.color: root.stroke }
                        }
                        DButton { text: "Add"; accent: true; enabled: bmUrl.text.length > 0
                                  onClicked: { darkelf.addBookmark(bmTitle.text || bmUrl.text, bmUrl.text); bmTitle.text=""; bmUrl.text="" } }
                    }
                    RowLayout {
                        Layout.leftMargin: 26
                        Text { text: "Show bookmarks bar"; color: root.textCol; font.pixelSize: 13 }
                        Switch { checked: root.showBookmarksBar; onToggled: root.showBookmarksBar = checked }
                    }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        Layout.leftMargin: 26; Layout.rightMargin: 26; Layout.bottomMargin: 22
                        clip: true; model: root.bookmarks; spacing: 6
                        delegate: Rectangle {
                            width: ListView.view.width; height: 50; radius: 12; color: root.card; border.color: root.stroke
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 10; spacing: 12
                                Rectangle {
                                    width: 26; height: 26; radius: 7; color: root.accent
                                    Text { anchors.centerIn: parent; text: (modelData.title||"?").charAt(0).toUpperCase(); color: "#0a0b10"; font.bold: true; font.pixelSize: 12 }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 0
                                    Text { text: modelData.title || modelData.url; color: root.textCol; font.pixelSize: 13; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Text { text: modelData.url; color: root.muted; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                                DButton { text: "Open"; onClicked: { var w=root.activeWeb(); if(w) w.url=modelData.url; settingsPage.close() } }
                                DButton { text: "Remove"; danger: true; onClicked: darkelf.removeBookmark(modelData.url) }
                            }
                        }
                    }
                    Text {
                        visible: root.bookmarks.length === 0
                        text: "No bookmarks yet — use the ☆ star in the address bar, or add one above."
                        color: root.muted; font.pixelSize: 13; Layout.leftMargin: 26; Layout.bottomMargin: 22
                    }
                }

                // ---- About (clean, explanatory, with links) ----
                ScrollView {
                    contentWidth: availableWidth; clip: true
                    ColumnLayout {
                        width: settingsPage.width - 244
                        spacing: 14

                        RowLayout {
                            Layout.leftMargin: 26; Layout.rightMargin: 26; Layout.topMargin: 26; spacing: 16
                            Image { source: "../assets/darkelf-mark.png"; sourceSize.width: 72; sourceSize.height: 72; Layout.preferredWidth: 72; Layout.preferredHeight: 72; fillMode: Image.PreserveAspectFit }
                            ColumnLayout {
                                spacing: 4; Layout.fillWidth: true
                                Text { text: "Darkelf Shadow"; color: root.textCol; font.pixelSize: 24; font.bold: true }
                                RowLayout {
                                    spacing: 8
                                    Rectangle { radius: 10; implicitHeight: 22; implicitWidth: verTxt.implicitWidth + 18; color: root.accentSoft; border.color: root.accent
                                                Text { id: verTxt; anchors.centerIn: parent; text: "v" + darkelf.appVersion; color: root.accent; font.pixelSize: 11; font.weight: Font.DemiBold } }
                                    Text { text: "LGPL-3.0-or-later"; color: root.muted; font.pixelSize: 11 }
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true; Layout.leftMargin: 26; Layout.rightMargin: 26
                            wrapMode: Text.WordWrap; lineHeight: 1.35
                            color: root.muted; font.pixelSize: 13
                            text: "A defense-in-depth privacy browser built on Qt WebEngine. Darkelf Shadow runs " +
                                  "entirely in memory — no disk-based cookies, cache, or history — and actively " +
                                  "blocks trackers, upgrades connections to HTTPS, and neutralizes browser " +
                                  "fingerprinting on-device. The MiniAI sentinel monitors request activity in real time."
                        }

                        Text { text: "WHAT'S PROTECTING YOU"; color: root.muted; font.pixelSize: 11; font.letterSpacing: 1.2; Layout.leftMargin: 26; Layout.topMargin: 4 }
                        Flow {
                            Layout.fillWidth: true; Layout.leftMargin: 26; Layout.rightMargin: 26; spacing: 8
                            FeatureChip { label: "No persistence" }
                            FeatureChip { label: "Fingerprint defense" }
                            FeatureChip { label: "Tracker filtering" }
                            FeatureChip { label: "HTTPS upgrade" }
                            FeatureChip { label: "WebRTC blocked" }
                            FeatureChip { label: "MiniAI sentinel" }
                        }

                        Text { text: "RESOURCES"; color: root.muted; font.pixelSize: 11; font.letterSpacing: 1.2; Layout.leftMargin: 26; Layout.topMargin: 6 }
                        Flow {
                            Layout.fillWidth: true; Layout.leftMargin: 26; Layout.rightMargin: 26; spacing: 10
                            LinkChip { label: "GitHub"; url: "https://github.com/Darkelf2024/Darkelf-Shadow" }
                            LinkChip { label: "PyPI"; url: "https://pypi.org/project/darkelf-shadow/" }
                            LinkChip { label: "License (LGPL-3.0)"; url: "https://www.gnu.org/licenses/lgpl-3.0.html" }
                            LinkChip { label: "Report an issue"; url: "https://github.com/Darkelf2024/Darkelf-Shadow/issues" }
                        }

                        Item { Layout.fillHeight: true }
                        Text {
                            Layout.leftMargin: 26; Layout.bottomMargin: 22
                            text: "© 2025 Dr. Kevin Moore · Darkelf Project — Shadow Edition"
                            color: root.muted; font.pixelSize: 11
                        }
                    }
                }
            }
        }
    }

    component InfoRow: RowLayout {
        property string label: ""
        property string value: ""
        Layout.fillWidth: true
        Layout.leftMargin: 26; Layout.rightMargin: 26; Layout.topMargin: 8
        Text { text: label; color: root.textCol; font.pixelSize: 14; Layout.fillWidth: true }
        Text { text: value; color: root.accent; font.pixelSize: 13; font.weight: Font.DemiBold }
    }

    // ===================== Delete data confirm =====================
    FluidPopup {
        id: nukeConfirm
        width: 420; height: 200
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 24; spacing: 14
            Text { text: "Delete browsing data"; color: root.textCol; font.pixelSize: 17; font.bold: true }
            Text {
                Layout.fillWidth: true; wrapMode: Text.WordWrap
                text: "This wipes all cookies, cache and visited links, then closes the browser."
                color: root.muted; font.pixelSize: 13
            }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                DButton { text: "Cancel"; onClicked: nukeConfirm.close() }
                DButton { text: "Delete & Quit"; danger: true; onClicked: { nukeConfirm.close(); darkelf.nuke() } }
            }
        }
    }

    // ===================== tab model + first tab =====================
    ListModel { id: tabsModel }
    Component.onCompleted: { root.reloadBookmarks(); root.addTab("") }
}
