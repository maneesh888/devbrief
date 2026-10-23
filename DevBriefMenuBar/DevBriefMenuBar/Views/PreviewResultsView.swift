import SwiftUI

struct PreviewResultsView: View {
    @Environment(\.dismiss) private var dismiss
    let entries: [LogEntry]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Preview").font(.headline)
            Text("Not saved — nothing was written to the log.")
                .font(.caption)
                .foregroundStyle(.secondary)

            if entries.isEmpty {
                Text("No activity found for the selected range.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(Array(entries.enumerated()), id: \.offset) { _, entry in
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(entry.date) · \(entry.project)").font(.caption).bold()
                                Text(entry.text).font(.caption)
                            }
                        }
                    }
                }
                .frame(minHeight: 180, maxHeight: 320)
            }

            HStack {
                Spacer()
                Button("Close") { dismiss() }
                    .keyboardShortcut(.defaultAction)
            }
        }
        .padding(16)
        .frame(width: 420)
    }
}
