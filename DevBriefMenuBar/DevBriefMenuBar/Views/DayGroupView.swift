import SwiftUI

/// One day's entries: a date heading ("27 Oct"), then each project's
/// numbered list. The project name is only shown when it adds information.
struct DayGroupView: View {
    let group: DayGroup

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(group.title).font(.caption).bold()
            ForEach(group.entries) { entry in
                VStack(alignment: .leading, spacing: 2) {
                    Text(entry.project).font(.caption2).foregroundStyle(.secondary)
                    Text(entry.text).font(.caption)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .padding(.vertical, 2)
    }
}
