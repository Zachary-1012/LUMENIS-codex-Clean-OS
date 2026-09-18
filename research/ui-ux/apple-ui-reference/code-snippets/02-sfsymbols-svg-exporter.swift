// 来源: https://github.com/davedelong/sfsymbols
// 文件: Sources/SFSymbolsCore/Exporters/SVGExporter.swift (SHA: 12bf2d16616c3624f432e6a97e2b91b89a8d6fec)
// 用途: 把 Glyph 枚举出来的 CGPath 元素写成标准 SVG path 字符串。
//       学习要点: SVG y 轴翻转(scale(1,-1))、fill-rule、stroke-width、方向标注。
// 许可: MIT

import Foundation

public struct SVGExporter: Exporter {

    private func format(_ point: CGPoint) -> String {
        return "\(point.x),\(point.y)"
    }

    public func exportGlyph(_ glyph: Glyph, in font: Font, to folder: URL) throws {
        let name = "\(glyph.fullName).svg"
        let file = folder.appendingPathComponent(name)
        let glyphData = data(for: glyph, in: font)
        try glyphData.write(to: file)
    }

    public func data(for glyph: Glyph, in font: Font) -> Data {
        var lines = Array<String>()
        if let restriction = glyph.restrictionNote {
            lines.append("<!--")
            lines.append("    " + restriction)
            lines.append("-->")
        }

        let direction = glyph.allowsMirroring ? "" : " direction='ltr'"
        lines.append("<svg width='\(glyph.boundingBox.width)px' height='\(glyph.boundingBox.height)px'\(direction) xmlns='http://www.w3.org/2000/svg' version='1.1'>")
        lines.append("<g fill-rule='nonzero' transform='scale(1,-1) translate(0,-\(glyph.boundingBox.height))'>")
        lines.append("<path fill='black' stroke='black' fill-opacity='1.0' stroke-width='\(font.strokeWidth)' d='")
        glyph.enumerateElements { (_, element) in
            switch element {
                case .move(let p): lines.append("    M \(format(p))")
                case .line(let p): lines.append("    L \(format(p))")
                case .quadCurve(let p, let c): lines.append("    Q \(format(p)) \(format(c))")
                case .curve(let p, let c1, let c2): lines.append("    C \(format(p)) \(format(c1)) \(format(c2))")
                case .close: lines.append("    Z")
            }
        }
        lines.append("' />")
        lines.append("</g>")
        lines.append("</svg>")

        let svg = lines.joined(separator: "\n")

        return Data(svg.utf8)
    }
}

// 同目录其他导出器(可在原仓库 Sources/SFSymbolsCore/Exporters/ 查看):
// - PNGExporter.swift      位图栅格化
// - PDFExporter.swift      PDF 矢量
// - IconsetExporter.swift  多尺寸 iconset
// - iOSExporter.swift      iOS 资产目录结构
// - macOSExporter.swift    macOS 资产目录结构
