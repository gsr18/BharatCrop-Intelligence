"use client";

import { Fragment, useMemo, type ReactNode } from "react";

type Align = "left" | "center" | "right";

type Block =
  | { kind: "heading"; level: number; content: string }
  | { kind: "paragraph"; content: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "quote"; content: string }
  | { kind: "code"; language: string; content: string }
  | {
      kind: "table";
      header: string[];
      aligns: Align[];
      rows: string[][];
    }
  | { kind: "rule" };

const INLINE_PATTERN =
  /(`[^`\n]+`|\*\*[^*\n]+\*\*|\*[^*\n]+\*|~~[^~\n]+~~|\[[^\]\n]+\]\(https?:\/\/[^)\s]+\))/g;

const ORDERED_ITEM = /^\s*\d+[.)]\s+(.*)$/;
const UNORDERED_ITEM = /^\s*[-*+]\s+(.*)$/;

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(INLINE_PATTERN);
  return parts
    .filter((part) => part !== "")
    .map((part, index) => {
      const key = `${keyPrefix}-${index}`;
      if (part.startsWith("`") && part.endsWith("`")) {
        return <code key={key}>{part.slice(1, -1)}</code>;
      }
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={key}>
            {renderInline(part.slice(2, -2), `${key}-strong`)}
          </strong>
        );
      }
      if (part.startsWith("~~") && part.endsWith("~~")) {
        return <del key={key}>{part.slice(2, -2)}</del>;
      }
      if (part.startsWith("*") && part.endsWith("*")) {
        return (
          <em key={key}>{renderInline(part.slice(1, -1), `${key}-em`)}</em>
        );
      }
      const link = /^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/.exec(part);
      if (link) {
        return (
          <a href={link[2]} key={key} rel="noreferrer" target="_blank">
            {link[1]}
            <span aria-hidden="true"> ↗</span>
          </a>
        );
      }
      return <Fragment key={key}>{part}</Fragment>;
    });
}

function splitRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function parseAlignments(line: string | undefined): Align[] | null {
  if (line === undefined || !line.includes("-")) return null;
  const cells = splitRow(line);
  if (!cells.length) return null;
  if (!cells.every((cell) => /^:?-{3,}:?$/.test(cell))) return null;
  return cells.map((cell) => {
    const left = cell.startsWith(":");
    const right = cell.endsWith(":");
    if (left && right) return "center";
    if (right) return "right";
    return "left";
  });
}

function isRule(line: string) {
  return /^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line);
}

function startsBlock(lines: string[], index: number) {
  const line = lines[index];
  if (!line.trim()) return true;
  if (/^\s*```/.test(line)) return true;
  if (/^\s*#{1,6}\s+/.test(line)) return true;
  if (/^\s*>/.test(line)) return true;
  if (ORDERED_ITEM.test(line) || UNORDERED_ITEM.test(line)) return true;
  if (isRule(line)) return true;
  return line.includes("|") && parseAlignments(lines[index + 1]) !== null;
}

function parseBlocks(content: string): Block[] {
  const lines = content.replace(/\r\n?/g, "\n").split("\n");
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = /^\s*```(.*)$/.exec(line);
    if (fence) {
      const language = fence[1].trim();
      const code: string[] = [];
      index += 1;
      while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) {
        code.push(lines[index]);
        index += 1;
      }
      index += 1;
      blocks.push({ kind: "code", language, content: code.join("\n") });
      continue;
    }

    const heading = /^\s*(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      blocks.push({
        kind: "heading",
        level: heading[1].length,
        content: heading[2].trim(),
      });
      index += 1;
      continue;
    }

    if (isRule(line)) {
      blocks.push({ kind: "rule" });
      index += 1;
      continue;
    }

    const aligns = line.includes("|")
      ? parseAlignments(lines[index + 1])
      : null;
    if (aligns) {
      const header = splitRow(line);
      const rows: string[][] = [];
      index += 2;
      while (index < lines.length && lines[index].trim()) {
        if (!lines[index].includes("|")) break;
        rows.push(splitRow(lines[index]));
        index += 1;
      }
      blocks.push({ kind: "table", header, aligns, rows });
      continue;
    }

    if (/^\s*>/.test(line)) {
      const quote: string[] = [];
      while (index < lines.length && /^\s*>/.test(lines[index])) {
        quote.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      blocks.push({ kind: "quote", content: quote.join(" ").trim() });
      continue;
    }

    const ordered = ORDERED_ITEM.test(line);
    const unordered = UNORDERED_ITEM.test(line);
    if (ordered || unordered) {
      const items: string[] = [];
      const pattern = ordered ? ORDERED_ITEM : UNORDERED_ITEM;
      while (index < lines.length) {
        const item = pattern.exec(lines[index]);
        if (item) {
          items.push(item[1].trim());
          index += 1;
          continue;
        }
        // Treat indented continuation lines as part of the previous item.
        if (
          items.length &&
          lines[index].trim() &&
          /^\s{2,}\S/.test(lines[index])
        ) {
          items[items.length - 1] += ` ${lines[index].trim()}`;
          index += 1;
          continue;
        }
        break;
      }
      blocks.push({ kind: "list", ordered, items });
      continue;
    }

    const paragraph: string[] = [line.trim()];
    index += 1;
    while (index < lines.length && !startsBlock(lines, index)) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push({ kind: "paragraph", content: paragraph.join(" ") });
  }

  return blocks;
}

export function MarkdownMessage({ content }: { content: string }) {
  const blocks = useMemo(() => parseBlocks(content), [content]);

  return (
    <div className="markdown-body">
      {blocks.map((block, index) => {
        const key = `${block.kind}-${index}`;
        switch (block.kind) {
          case "heading": {
            const Heading =
              block.level <= 2 ? "h2" : block.level === 3 ? "h3" : "h4";
            return (
              <Heading key={key}>{renderInline(block.content, key)}</Heading>
            );
          }
          case "paragraph":
            return <p key={key}>{renderInline(block.content, key)}</p>;
          case "quote":
            return (
              <blockquote key={key}>
                {renderInline(block.content, key)}
              </blockquote>
            );
          case "code":
            return (
              <pre key={key}>
                <code>{block.content}</code>
              </pre>
            );
          case "rule":
            return <hr key={key} />;
          case "list": {
            const List = block.ordered ? "ol" : "ul";
            return (
              <List key={key}>
                {block.items.map((item, itemIndex) => (
                  <li key={`${key}-item-${itemIndex}`}>
                    {renderInline(item, `${key}-item-${itemIndex}`)}
                  </li>
                ))}
              </List>
            );
          }
          case "table":
            return (
              <div className="md-table-wrap" key={key}>
                <table>
                  <thead>
                    <tr>
                      {block.header.map((cell, cellIndex) => (
                        <th
                          key={`${key}-head-${cellIndex}`}
                          style={{
                            textAlign: block.aligns[cellIndex] ?? "left",
                          }}
                        >
                          {renderInline(cell, `${key}-head-${cellIndex}`)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {block.rows.map((row, rowIndex) => (
                      <tr key={`${key}-row-${rowIndex}`}>
                        {row.map((cell, cellIndex) => (
                          <td
                            key={`${key}-cell-${rowIndex}-${cellIndex}`}
                            style={{
                              textAlign: block.aligns[cellIndex] ?? "left",
                            }}
                          >
                            {renderInline(
                              cell,
                              `${key}-cell-${rowIndex}-${cellIndex}`,
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          default:
            return null;
        }
      })}
    </div>
  );
}
