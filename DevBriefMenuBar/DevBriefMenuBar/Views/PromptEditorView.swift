import SwiftUI

struct PromptEditorView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var draftText: String = ""
    @State private var defaultPrompt: String = ""
    @State private var isUsingOverride = false
    @State private var errorMessage: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Summary Prompt").font(.headline)
            Text(isUsingOverride
                 ? "This is your saved override. Editing and saving updates it; Reset removes it and shows the built-in default below."
                 : "This is the built-in default prompt devbrief sends to every brief. Edit it and Save to override it.")
                .font(.caption)
                .foregroundStyle(.secondary)

            TextEditor(text: $draftText)
                .font(.system(.body, design: .monospaced))
                .frame(minHeight: 220)
                .overlay(RoundedRectangle(cornerRadius: 4).stroke(.separator))

            if let errorMessage {
                Text(errorMessage).font(.caption).foregroundStyle(.red)
            }

            HStack {
                Button("Reset to Default", role: .destructive) { resetToDefault() }
                    .disabled(!isUsingOverride)
                Spacer()
                Button("Cancel") { dismiss() }
                Button("Save") { save() }
                    .keyboardShortcut(.defaultAction)
            }
        }
        .padding(16)
        .frame(width: 460)
        .onAppear { load() }
    }

    private func load() {
        let override = PromptStore.loadOverride()
        if !override.isEmpty {
            draftText = override
            isUsingOverride = true
        }
        do {
            defaultPrompt = try DevBriefCLI.defaultPrompt()
            if override.isEmpty {
                draftText = defaultPrompt
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func save() {
        do {
            try PromptStore.save(draftText)
            isUsingOverride = true
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func resetToDefault() {
        do {
            try PromptStore.resetToDefault()
            draftText = defaultPrompt
            isUsingOverride = false
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
