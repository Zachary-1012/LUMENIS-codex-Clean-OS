// 来源: https://github.com/raphaelhanneken/iconizer
// 文件: Iconizer/Models/AppIcon.swift (SHA: 38a7aac47b1c30b72ef3ebe5066a140ffc390964)
// 用途: App 图标资产目录(Asset Catalog.appiconset/Contents.json)数据模型，
//       演示 iOS/macOS/watchOS/iMessage 多 idiom、size、@2x/@3x scale 的命名与导出规则。
// 同目录模型: AssetCatalog.swift / ImageSet.swift / LaunchImage.swift / iMessageIcon.swift
// 许可: MIT

import Cocoa

class AppIcon: Codable {
    private static let marketing = "marketing"

    class var directory: String {
        return Constants.Directory.appIcon
    }

    class var `extension`: String {
        return Constants.AssetExtension.appIcon
    }

    let idiom: String
    let size: AssetSize
    let scale: AssetScale
    let role: String?       // Apple Watch
    let subtype: String?    // Apple Watch
    let platform: String?   // iMessage

    // 导出文件名按实际像素: icon-<scaledWidth>.png，相同像素自动复用
    var filename: String {
        let scaledWidth = Int(size.width * Float(scale.value))
        return "icon-\(scaledWidth).png"
    }

    private enum ReadKeys: String, CodingKey {
        case idiom, size, scale, role, subtype, platform
    }

    private enum WriteKeys: String, CodingKey {
        case idiom, size, scale, role, subtype, platform, filename
    }

    init(idiom: String, size: AssetSize, scale: AssetScale, role: String? = nil,
         subtype: String? = nil, platform: String?) {
        self.idiom = idiom
        self.size = size
        self.scale = scale
        self.role = role
        self.subtype = subtype
        self.platform = platform
    }

    required init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: ReadKeys.self)
        let idiom = try container.decode(String.self, forKey: .idiom)

        guard let scale = AssetScale(rawValue: try container.decode(String.self, forKey: .scale)) else {
            throw AssetCatalogError.invalidFormat(format: .scale)
        }
        let size = try AssetSize(size: try container.decode(String.self, forKey: .size))

        self.idiom = idiom
        self.size = size
        self.scale = scale

        self.role = try container.decodeIfPresent(String.self, forKey: .role)
        self.subtype = try container.decodeIfPresent(String.self, forKey: .subtype)
        self.platform = try container.decodeIfPresent(String.self, forKey: .platform)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: WriteKeys.self)
        try container.encode(idiom, forKey: .idiom)
        try container.encode(size.string, forKey: .size)
        try container.encode(scale.rawValue, forKey: .scale)
        try container.encode(filename, forKey: .filename)
        try container.encodeIfPresent(role, forKey: .role)
        try container.encodeIfPresent(subtype, forKey: .subtype)
        try container.encodeIfPresent(platform, forKey: .platform)
    }
}

extension AppIcon: Asset {
    static let resourcePrefix = "AppIcon_"

    static func directory(named: String) -> String {
        return "\(directory)/\(named).\(self.extension)"
    }

    func save(_ image: [ImageOrientation: NSImage], aspect: AspectMode?, to url: URL) throws {
        guard let image = image[.all] else {
            throw AssetCatalogError.missingImage
        }

        let url = url.appendingPathComponent(filename, isDirectory: false)
        // 同名像素文件已存在则跳过(Contents.json 复用)
        guard !FileManager.default.fileExists(atPath: url.path) else {
            return
        }

        guard let resized = image.resize(toSize: size.multiply(scale), aspectMode: aspect ?? .fit) else {
            throw AssetCatalogError.rescalingImageFailed
        }
        // marketing 1024x1024 图标不允许 alpha 通道(App Store 硬性要求)
        try resized.savePng(url: url, withoutAlpha: idiom.contains(AppIcon.marketing))
    }
}
