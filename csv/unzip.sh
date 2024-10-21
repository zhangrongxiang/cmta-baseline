#!/bin/bash

# 遍历当前目录下的所有 .zip 文件
for zip_file in *.zip; do
  # 检查文件是否存在
  if [ -f "$zip_file" ]; then
    echo "解压: $zip_file"

    # 解压到相应的目录中
    unzip -q "$zip_file"
    echo "$zip_file 已成功解压
  else
    echo "没有找到 .zip 文件"
  fi
done
