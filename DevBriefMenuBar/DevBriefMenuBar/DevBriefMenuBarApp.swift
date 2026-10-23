import SwiftUI

@main
struct DevBriefMenuBarApp: App {
    var body: some Scene {
        MenuBarExtra("DevBrief", systemImage: "clock.badge.checkmark") {
            MenuContentView()
        }
        .menuBarExtraStyle(.window)
    }
}
