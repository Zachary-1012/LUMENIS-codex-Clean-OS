// 来源: https://github.com/SFSafeSymbols/SFSafeSymbols
// 文件: Sources/SFSafeSymbols/Initializers/UIKit/UIImage+SFSymbol.swift (SHA: 0f58fc682f4b32e8947a9574bca24d4e77176c99)
// 用途: 用类型安全的 SFSymbol 枚举替代裸字符串 systemName，
//       编译期即可检测图标名是否存在，避免线上问号方块。
// 同类初始化器目录:
//   Initializers/UIKit/   (UIImage / UIApplicationShortcutIcon)
//   Initializers/SwiftUI/ (Image)
//   Initializers/AppKit/  (NSImage)
//   Initializers/AppIntents/
// 枚举生成器: SymbolsGenerator/ (从 Apple 官方符号目录自动生成全部静态 case)
// 许可: MIT

#if canImport(UIKit)

import UIKit

@available(iOS 13.0, tvOS 13.0, watchOS 6.0, visionOS 1.0, *)
public extension UIImage {

    /// Creates an image object that contains a system symbol image.
    ///
    /// - Parameter systemSymbol: The `SFSymbol` describing this image.
    convenience init(systemSymbol: SFSymbol) {
        self.init(systemName: systemSymbol.rawValue)!
    }

#if !os(watchOS)
    /// Creates an image object that contains a system symbol image appropriate for the specified traits.
    convenience init(systemSymbol: SFSymbol, compatibleWith traitCollection: UITraitCollection?) {
        self.init(systemName: systemSymbol.rawValue, compatibleWith: traitCollection)!
    }
#endif

    /// Creates an image object that contains a system symbol image with the specified configuration.
    convenience init(systemSymbol: SFSymbol, withConfiguration configuration: UIImage.Configuration?) {
        self.init(systemName: systemSymbol.rawValue, withConfiguration: configuration)!
    }

    /// Creates an image object that contains a system symbol image with the configuration and variable value you specify.
    /// - Parameter variableValue: 0...1，用于音量/信号等可变填充图标
    @available(iOS 16.0, tvOS 16.0, watchOS 9.0, visionOS 1.0, *)
    convenience init(systemSymbol: SFSymbol, variableValue: Double, configuration: UIImage.Configuration?) {
        self.init(systemName: systemSymbol.rawValue, variableValue: variableValue, configuration: configuration)!
    }
}

#endif

// SwiftUI 侧等价用法(Initializers/SwiftUI/Image+SFSymbol.swift):
//   Image(systemSymbol: .heartFill)
//   Image(systemSymbol: .speakerWave2, variableValue: 0.5)
