// 来源: https://github.com/yc-w-cn/macos-compliant-icon-generator
// 文件: src/components/ImageUploader.tsx (SHA: c38dc3e81232dfd59601490d26861f12fa385fbf)
// 用途: 按 Apple Human Interface Guidelines 把"填满画布"的图转成合规 macOS/iOS 图标:
//   规范要点(代码内硬编码, 与 HIG "App Icons and Images" 一致):
//     1) 画布 1024 x 1024 (canvasSize)
//     2) 实际内容区 832 x 832 (contentSize)，即内容占 13/16 = 81.25%，四周留 1/16 边距
//     3) 圆角半径 = 22% 内容边长 (cornerRadius = 0.22 * 832)
//     4) CSS 等价写法: width 81.25% + rounded-[17.875%]
//   技术栈: Canvas 2D 路径裁剪 quadraticCurveTo 绘制连续圆角矩形。
// 许可: MIT

"use client";
import React, { useState } from "react";
import { useDropzone } from "react-dropzone";

const ImageUploader: React.FC = () => {
  const [image, setImage] = useState<string | null>(null);
  const [roundedImage, setRoundedImage] = useState<string | null>(null);

  const { getRootProps, getInputProps } = useDropzone({
    accept: { "image/*": [".jpeg", ".png"] },
    onDrop: (acceptedFiles: any) => {
      const file = acceptedFiles[0];
      const reader = new FileReader();
      reader.onload = () => {
        const img = new Image();
        img.src = reader.result as string;
        img.onload = () => {
          setImage(img.src);
          const canvas = document.createElement("canvas");
          const ctx = canvas.getContext("2d");
          if (ctx) {
            // ===== HIG 尺寸常量: 1024 画布 / 832 内容 / 22% 圆角 =====
            const canvasSize = 1024;
            const contentSize = 832;
            const cornerRadius = (22 / 100) * contentSize;
            const offsetX = (canvasSize - contentSize) / 2;
            const offsetY = (canvasSize - contentSize) / 2;

            canvas.width = canvasSize;
            canvas.height = canvasSize;
            ctx.clearRect(0, 0, canvasSize, canvasSize);
            ctx.beginPath();

            // 四个连续圆角(quadraticCurveTo)
            ctx.moveTo(offsetX + cornerRadius, offsetY);
            ctx.lineTo(offsetX + contentSize - cornerRadius, offsetY);
            ctx.quadraticCurveTo(
              offsetX + contentSize, offsetY,
              offsetX + contentSize, offsetY + cornerRadius
            );
            ctx.lineTo(offsetX + contentSize, offsetY + contentSize - cornerRadius);
            ctx.quadraticCurveTo(
              offsetX + contentSize, offsetY + contentSize,
              offsetX + contentSize - cornerRadius, offsetY + contentSize
            );
            ctx.lineTo(offsetX + cornerRadius, offsetY + contentSize);
            ctx.quadraticCurveTo(
              offsetX, offsetY + contentSize,
              offsetX, offsetY + contentSize - cornerRadius
            );
            ctx.lineTo(offsetX, offsetY + cornerRadius);
            ctx.quadraticCurveTo(
              offsetX, offsetY,
              offsetX + cornerRadius, offsetY
            );
            ctx.closePath();
            ctx.clip();

            // 在裁剪区内绘制 832x832 内容
            ctx.drawImage(img, offsetX, offsetY, contentSize, contentSize);
            setRoundedImage(canvas.toDataURL());
          }
        };
      };
      reader.readAsDataURL(file);
    },
  });
  // JSX 渲染部分见原仓库
  return null as any;
};

export default ImageUploader;

/*
SwiftUI 等价尺寸(供原生开发参考):
  Canvas 1024pt, content 832pt (0.8125), 圆角 = 0.22 * 832 ≈ 183pt
  RoundedRectangle(cornerRadius: 183, style: .continuous)
注意: Apple 实际使用的是"连续圆角"(continuous / squircle)，
      不是普通四分之一圆弧；SwiftUI 必须指定 style: .continuous。
*/
