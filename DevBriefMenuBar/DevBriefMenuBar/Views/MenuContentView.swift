import AppKit
import SwiftUI

struct MenuContentView: View {
    @State private var entries: [LogEntry] = []
    @State private var isGenerating = false
    @State private var jobLoaded = false
    @State private var statusMessage: String?
    @State private var fromDate = Calendar.current.date(byAdding: .day, value: -1, to: Date()) ?? Date()
    @State private var toDate = Calendar.current.date(byAdding: .day, value: -1, to: Date()) ?? Date()
    @State private var generateProgress: (done: Int, total: Int)?
    @State private var previewOnly = false
    @State private var previewEntries: [LogEntry] = []
    @State private var showPreviewResults = false
    @State private var showPromptEditor = false
    @State private var sourceStates: [String: Bool] = [:]

    private static let sourceOrder = ["claude_code", "codex", "copilot"]
    private static let sourceDisplayNames = [
        "claude_code": "Claude Code",
        "codex": "Codex",
        "copilot": "Copilot",
    ]

    private static let isoFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.timeZone = .current
        return f
    }()

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("devbrief").font(.headline)

            if let statusMessage {
                Text(statusMessage)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(3)
            }

            Divider()

            HStack {
                Text("From").foregroundStyle(.secondary)
                DatePicker("", selection: $fromDate, in: ...Date(), displayedComponents: .date)
                    .datePickerStyle(.compact)
                    .labelsHidden()
                    .fixedSize()
                    .onChange(of: fromDate) { _, newValue in
                        if newValue > toDate { toDate = newValue }
                    }
                Spacer()
                Text("To").foregroundStyle(.secondary)
                DatePicker("", selection: $toDate, in: ...Date(), displayedComponents: .date)
                    .datePickerStyle(.compact)
                    .labelsHidden()
                    .fixedSize()
                    .onChange(of: toDate) { _, newValue in
                        if newValue < fromDate { fromDate = newValue }
                    }
            }

            HStack {
                Button(generateButtonTitle) {
                    generateNow()
                }
                .disabled(isGenerating)

                Spacer()

                Toggle("Preview only", isOn: $previewOnly)
                    .toggleStyle(.checkbox)
                    .font(.caption)
            }

            Toggle("Daily automatic run", isOn: Binding(
                get: { jobLoaded },
                set: { toggleJob($0) }
            ))

            HStack {
                Menu("Sources") {
                    ForEach(Self.sourceOrder, id: \.self) { name in
                        Toggle(Self.sourceDisplayNames[name] ?? name, isOn: sourceBinding(name))
                    }
                }
                .fixedSize()
                Spacer()
                Text(enabledSourcesSummary)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.tail)
            }

            Divider()

            Text("Recent entries").font(.subheadline).foregroundStyle(.secondary)
            if entries.isEmpty {
                Text("(none yet)").font(.caption).foregroundStyle(.secondary)
            } else {
                ForEach(entries.prefix(5)) { entry in
                    VStack(alignment: .leading, spacing: 2) {
                        Text("\(entry.date) · \(entry.project)").font(.caption).bold()
                        Text(entry.text).font(.caption).lineLimit(3)
                    }
                    .padding(.vertical, 2)
                }
            }

            Divider()

            Button("Open Log File") { openLogFile() }
            Button("Edit Prompt…") { showPromptEditor = true }
            Button("Clear All Data", role: .destructive) { clearAll() }

            Divider()

            Button("Quit") {
                NSApplication.shared.terminate(nil)
            }
        }
        .padding(12)
        .frame(width: 320)
        .onAppear { refresh() }
        .sheet(isPresented: $showPromptEditor) {
            PromptEditorView()
        }
        .sheet(isPresented: $showPreviewResults) {
            PreviewResultsView(entries: previewEntries)
        }
    }

    private func refresh() {
        jobLoaded = LaunchAgentController.isLoaded()
        do {
            entries = try DevBriefCLI.fetchLog(limit: 5)
            sourceStates = try DevBriefCLI.listSources()
            statusMessage = nil
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    private var enabledSourcesSummary: String {
        let enabled = Self.sourceOrder
            .filter { sourceStates[$0] ?? true }
            .compactMap { Self.sourceDisplayNames[$0] }
        return enabled.isEmpty ? "None" : enabled.joined(separator: ", ")
    }

    private func sourceBinding(_ name: String) -> Binding<Bool> {
        Binding(
            get: { sourceStates[name] ?? true },
            set: { newValue in
                sourceStates[name] = newValue
                do {
                    try DevBriefCLI.setSource(name, enabled: newValue)
                } catch {
                    statusMessage = error.localizedDescription
                }
            }
        )
    }

    private var generateButtonTitle: String {
        guard isGenerating else { return "Generate" }
        guard let generateProgress, generateProgress.total > 1 else { return "Generating…" }
        return "Generating… (\(generateProgress.done)/\(generateProgress.total))"
    }

    private func datesInRange() -> [Date] {
        var dates: [Date] = []
        var day = Calendar.current.startOfDay(for: fromDate)
        let lastDay = Calendar.current.startOfDay(for: toDate)
        while day <= lastDay {
            dates.append(day)
            guard let next = Calendar.current.date(byAdding: .day, value: 1, to: day) else { break }
            day = next
        }
        return dates
    }

    private func generateNow() {
        let days = datesInRange()
        let preview = previewOnly
        isGenerating = true
        generateProgress = (0, days.count)
        statusMessage = nil
        DispatchQueue.global(qos: .userInitiated).async {
            var collectedPreviewEntries: [LogEntry] = []
            for (index, day) in days.enumerated() {
                let dateString = Self.isoFormatter.string(from: day)
                do {
                    if preview {
                        collectedPreviewEntries += try DevBriefCLI.preview(date: dateString)
                    } else {
                        _ = try DevBriefCLI.generate(date: dateString)
                    }
                } catch {
                    DispatchQueue.main.async {
                        isGenerating = false
                        generateProgress = nil
                        statusMessage = error.localizedDescription
                    }
                    return
                }
                DispatchQueue.main.async {
                    generateProgress = (index + 1, days.count)
                }
            }
            DispatchQueue.main.async {
                isGenerating = false
                generateProgress = nil
                if preview {
                    previewEntries = collectedPreviewEntries
                    showPreviewResults = true
                } else {
                    refresh()
                }
            }
        }
    }

    private func toggleJob(_ newValue: Bool) {
        do {
            try LaunchAgentController.setLoaded(newValue)
            jobLoaded = newValue
            statusMessage = nil
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    private func openLogFile() {
        let path = NSHomeDirectory() + "/.devbrief/devbrief.log"
        NSWorkspace.shared.open(URL(fileURLWithPath: path))
    }

    private func clearAll() {
        do {
            try DevBriefCLI.clearAll()
            refresh()
        } catch {
            statusMessage = error.localizedDescription
        }
    }
}
