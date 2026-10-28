import Foundation

struct LogEntry: Identifiable {
    let id = UUID()
    let date: String
    let project: String
    let repoRoot: String
    let text: String
}

struct DayGroup: Identifiable {
    let date: String
    let entries: [LogEntry]
    var id: String { date }

    /// "2026-10-27" -> "27 Oct"; falls back to the raw string if it can't be parsed.
    var title: String {
        guard let day = Self.isoFormatter.date(from: date) else { return date }
        return Self.titleFormatter.string(from: day)
    }

    /// Groups consecutive entries sharing a date, keeping the incoming order.
    static func group(_ entries: [LogEntry]) -> [DayGroup] {
        var groups: [DayGroup] = []
        for entry in entries {
            if let last = groups.last, last.date == entry.date {
                groups[groups.count - 1] = DayGroup(date: last.date, entries: last.entries + [entry])
            } else {
                groups.append(DayGroup(date: entry.date, entries: [entry]))
            }
        }
        return groups
    }

    private static let isoFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.timeZone = .current
        return f
    }()

    private static let titleFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "d MMM"
        f.timeZone = .current
        return f
    }()
}
