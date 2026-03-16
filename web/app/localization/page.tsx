"use client";

import * as React from "react";
import { IconDeviceFloppy, IconRefresh, IconSearch } from "@tabler/icons-react";
import { toast } from "sonner";

import { AppSidebar } from "@/components/app-sidebar";
import { SiteHeader } from "@/components/site-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { SidebarInset } from "@/components/ui/sidebar";
import { Toaster } from "@/components/ui/sonner";
import { Spinner } from "@/components/ui/spinner";
import { useCanEdit } from "@/hooks";
import { localizationApi, type LocalizationData } from "@/lib/api";

type LocaleValues = Record<string, string>;

const TEMPLATE_TOKEN_HTML =
  '<span class="rounded-[2px] bg-amber-300/40 text-amber-800 dark:bg-amber-400/20 dark:text-amber-300">{?}</span>';
const PLACEHOLDER_TOKEN = "{?}";
const PLACEHOLDER_REGEX = /\{\?\}/g;
const HTML_TAG_PATTERN = /<\/?([a-z][a-z0-9-]*)\b[^>]*>/gi;
const EDITOR_PLACEHOLDER_MARKER = "\uF000";

const BLOCK_TAGS = new Set(["DIV", "P", "LI", "PRE"]);

type TagStyles = {
  bold: number;
  italic: number;
  underline: number;
  strike: number;
  code: number;
};

function cloneLocalization(data: LocalizationData): LocalizationData {
  const next: LocalizationData = {};
  for (const [locale, values] of Object.entries(data || {})) {
    next[locale] = { ...(values || {}) };
  }
  return next;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getInitialTagStyles(): TagStyles {
  return {
    bold: 0,
    italic: 0,
    underline: 0,
    strike: 0,
    code: 0,
  };
}

function updateTagStyles(
  styles: TagStyles,
  tagName: string,
  isClosing: boolean,
): void {
  const delta = isClosing ? -1 : 1;
  const apply = (key: keyof TagStyles) => {
    styles[key] = Math.max(0, styles[key] + delta);
  };

  switch (tagName) {
    case "b":
    case "strong":
      apply("bold");
      break;
    case "i":
    case "em":
      apply("italic");
      break;
    case "u":
      apply("underline");
      break;
    case "s":
    case "strike":
    case "del":
      apply("strike");
      break;
    case "code":
    case "pre":
      apply("code");
      break;
    default:
      break;
  }
}

function styleClassesToString(styles: TagStyles): string {
  const classes: string[] = [];
  if (styles.bold > 0) classes.push("font-semibold");
  if (styles.italic > 0) classes.push("italic");
  if (styles.underline > 0) classes.push("underline");
  if (styles.strike > 0) classes.push("line-through");
  if (styles.code > 0) classes.push("font-mono");
  return classes.join(" ");
}

function renderStyledChunk(chunk: string, styles: TagStyles): string {
  if (!chunk) return "";
  const chunkHtml = escapeHtml(chunk).replace(/\{\?\}/g, TEMPLATE_TOKEN_HTML);
  const classes = styleClassesToString(styles);
  if (!classes) return chunkHtml;
  return `<span class="${classes}">${chunkHtml}</span>`;
}

function highlightTemplateTokens(value: string): string {
  const source = String(value || "");
  const styles = getInitialTagStyles();
  let html = "";
  let cursor = 0;

  HTML_TAG_PATTERN.lastIndex = 0;
  let match = HTML_TAG_PATTERN.exec(source);
  while (match) {
    const token = match[0];
    const tagName = String(match[1] || "").toLowerCase();
    const start = match.index ?? 0;

    if (start > cursor) {
      html += renderStyledChunk(source.slice(cursor, start), styles);
    }

    const isClosing = token.startsWith("</");
    if (!isClosing) updateTagStyles(styles, tagName, false);
    html += renderStyledChunk(token, styles);
    if (isClosing) updateTagStyles(styles, tagName, true);

    cursor = start + token.length;
    match = HTML_TAG_PATTERN.exec(source);
  }

  if (cursor < source.length) {
    html += renderStyledChunk(source.slice(cursor), styles);
  }

  return html || "&nbsp;";
}

function renderDisplayHtml(value: string): string {
  return highlightTemplateTokens(value).replace(/\n/g, "<br/>");
}

function countPlaceholders(value: string): number {
  return String(value || "").match(PLACEHOLDER_REGEX)?.length ?? 0;
}

function sanitizeEditableSegmentText(value: string): string {
  return String(value || "")
    .replace(/\r\n?/g, "\n")
    .replace(PLACEHOLDER_REGEX, "");
}

function splitTemplateSegments(value: string): string[] {
  return String(value || "").split(PLACEHOLDER_REGEX);
}

function normalizeSegmentsLength(
  segments: string[],
  placeholderCount: number,
): string[] {
  const expectedLength = placeholderCount + 1;
  const next = [...segments];

  if (next.length > expectedLength) {
    const overflow = next.slice(expectedLength).join("");
    next.length = expectedLength;
    next[expectedLength - 1] = `${next[expectedLength - 1] || ""}${overflow}`;
  }

  while (next.length < expectedLength) {
    next.push("");
  }

  return next.map((segment) => sanitizeEditableSegmentText(segment));
}

function joinSegmentsWithPlaceholders(
  segments: string[],
  placeholderCount: number,
): string {
  const normalized = normalizeSegmentsLength(segments, placeholderCount);
  let result = "";
  for (let index = 0; index < placeholderCount; index += 1) {
    result += `${normalized[index] || ""}${PLACEHOLDER_TOKEN}`;
  }
  result += normalized[placeholderCount] || "";
  return result;
}

function buildImmutableEditorHtml(
  value: string,
  placeholderCount: number,
): string {
  const segments = normalizeSegmentsLength(
    splitTemplateSegments(value),
    placeholderCount,
  );
  let html = "";

  for (let index = 0; index < segments.length; index += 1) {
    html += `<span data-editor-segment="${index}">${escapeHtml(
      segments[index] || "",
    ).replace(/\n/g, "<br/>")}</span>`;
    if (index < placeholderCount) {
      html += `<span contenteditable="false" data-placeholder-token="true" class="mx-[1px] inline-flex rounded-[2px] bg-amber-300/40 px-[2px] text-amber-800 dark:bg-amber-400/20 dark:text-amber-300">${PLACEHOLDER_TOKEN}</span>`;
    }
  }

  return html;
}

function serializeEditorNode(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent || "";
  }

  if (!(node instanceof HTMLElement)) {
    return "";
  }

  if (node.dataset.placeholderToken === "true") {
    return EDITOR_PLACEHOLDER_MARKER;
  }

  if (node.tagName === "BR") {
    return "\n";
  }

  let text = "";
  node.childNodes.forEach((child) => {
    text += serializeEditorNode(child);
  });

  if (
    BLOCK_TAGS.has(node.tagName) &&
    text &&
    !text.endsWith("\n")
  ) {
    text += "\n";
  }

  return text;
}

function extractSegmentsFromEditor(
  root: HTMLElement,
  placeholderCount: number,
): {
  value: string;
  shouldRepair: boolean;
} {
  const placeholderNodes = root.querySelectorAll(
    '[data-placeholder-token="true"]',
  ).length;
  const segmentNodes = root.querySelectorAll("[data-editor-segment]").length;
  const serialized = Array.from(root.childNodes)
    .map((child) => serializeEditorNode(child))
    .join("");
  const serializedWithoutMarkers = serialized.split(EDITOR_PLACEHOLDER_MARKER).join("");

  let rawSegments: string[];
  if (serialized.includes(EDITOR_PLACEHOLDER_MARKER)) {
    rawSegments = serialized.split(EDITOR_PLACEHOLDER_MARKER);
  } else if (placeholderCount > 0 && PLACEHOLDER_REGEX.test(serialized)) {
    PLACEHOLDER_REGEX.lastIndex = 0;
    rawSegments = serialized.split(PLACEHOLDER_REGEX);
  } else {
    rawSegments = [serialized];
  }

  PLACEHOLDER_REGEX.lastIndex = 0;
  const normalizedSegments = normalizeSegmentsLength(rawSegments, placeholderCount);
  const hasRawPlaceholderText = PLACEHOLDER_REGEX.test(serializedWithoutMarkers);
  PLACEHOLDER_REGEX.lastIndex = 0;

  return {
    value: joinSegmentsWithPlaceholders(normalizedSegments, placeholderCount),
    shouldRepair:
      placeholderNodes !== placeholderCount ||
      segmentNodes !== placeholderCount + 1 ||
      (placeholderCount > 0 && !serialized.includes(EDITOR_PLACEHOLDER_MARKER)) ||
      hasRawPlaceholderText,
  };
}

function placeCaretAtEnd(element: HTMLElement): void {
  const selection = window.getSelection();
  if (!selection) return;

  const range = document.createRange();
  range.selectNodeContents(element);
  range.collapse(false);
  selection.removeAllRanges();
  selection.addRange(range);
}

function insertPlainTextAtCursor(text: string): void {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) {
    return;
  }

  const range = selection.getRangeAt(0);
  range.deleteContents();
  const textNode = document.createTextNode(text);
  range.insertNode(textNode);
  range.setStartAfter(textNode);
  range.collapse(true);
  selection.removeAllRanges();
  selection.addRange(range);
}

type ImmutablePlaceholderEditorProps = {
  templateValue: string;
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
};

function ImmutablePlaceholderEditor({
  templateValue,
  value,
  disabled = false,
  onChange,
}: ImmutablePlaceholderEditorProps) {
  const rootRef = React.useRef<HTMLDivElement | null>(null);
  const lastRenderedValueRef = React.useRef<string>("");
  const placeholderCount = React.useMemo(
    () => countPlaceholders(templateValue),
    [templateValue],
  );

  const renderValue = React.useCallback(
    (nextValue: string, moveCaretToEnd = false) => {
      const root = rootRef.current;
      if (!root) return;

      const normalizedValue = joinSegmentsWithPlaceholders(
        splitTemplateSegments(nextValue),
        placeholderCount,
      );

      root.innerHTML = buildImmutableEditorHtml(normalizedValue, placeholderCount);
      lastRenderedValueRef.current = normalizedValue;

      if (moveCaretToEnd && document.activeElement === root) {
        placeCaretAtEnd(root);
      }
    },
    [placeholderCount],
  );

  React.useLayoutEffect(() => {
    if (value !== lastRenderedValueRef.current) {
      renderValue(value);
    }
  }, [renderValue, value]);

  const syncFromDom = React.useCallback(
    (repairSelection = false) => {
      const root = rootRef.current;
      if (!root) return;

      const nextState = extractSegmentsFromEditor(root, placeholderCount);
      if (nextState.shouldRepair) {
        renderValue(nextState.value, repairSelection);
      } else {
        lastRenderedValueRef.current = nextState.value;
      }

      onChange(nextState.value);
    },
    [onChange, placeholderCount, renderValue],
  );

  return (
    <div className="rounded-md border border-border bg-muted/20">
      <div
        ref={rootRef}
        contentEditable={!disabled}
        suppressContentEditableWarning
        spellCheck={false}
        onInput={() => syncFromDom(false)}
        onBlur={() => syncFromDom(false)}
        onPaste={(event) => {
          event.preventDefault();
          insertPlainTextAtCursor(
            event.clipboardData.getData("text/plain") || "",
          );
          syncFromDom(true);
        }}
        className="min-h-[340px] whitespace-pre-wrap break-words px-3 py-2 font-mono text-[13px] leading-6 outline-none"
      />
    </div>
  );
}

export default function LocalizationPage() {
  const canEditLocalization = useCanEdit();

  const [sourceData, setSourceData] = React.useState<LocalizationData>({});
  const [draftData, setDraftData] = React.useState<LocalizationData>({});
  const [activeLocale, setActiveLocale] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [editorOpen, setEditorOpen] = React.useState(false);
  const [editorKey, setEditorKey] = React.useState<string | null>(null);
  const [editorTemplateValue, setEditorTemplateValue] = React.useState("");
  const [editorDraftValue, setEditorDraftValue] = React.useState("");

  const loadLocalization = React.useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await localizationApi.get();
      const normalized = cloneLocalization(data || {});
      const locales = Object.keys(normalized);
      setSourceData(normalized);
      setDraftData(cloneLocalization(normalized));
      setActiveLocale((currentLocale) =>
        currentLocale && locales.includes(currentLocale)
          ? currentLocale
          : (locales[0] ?? ""),
      );
    } catch (error: any) {
      const message = error?.message ?? "Не удалось загрузить локализацию.";
      setErrorMessage(message);
      toast.error("Ошибка загрузки локализации", { description: message });
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (!canEditLocalization) {
      setLoading(false);
      return;
    }
    loadLocalization();
  }, [canEditLocalization, loadLocalization]);

  const localeNames = React.useMemo(() => Object.keys(draftData), [draftData]);

  React.useEffect(() => {
    if (!localeNames.length) {
      if (activeLocale) setActiveLocale("");
      return;
    }
    if (!activeLocale || !localeNames.includes(activeLocale)) {
      setActiveLocale(localeNames[0]);
    }
  }, [activeLocale, localeNames]);

  const currentValues: LocaleValues = React.useMemo(
    () => draftData[activeLocale] || {},
    [draftData, activeLocale],
  );

  const sourceValues: LocaleValues = React.useMemo(
    () => sourceData[activeLocale] || {},
    [sourceData, activeLocale],
  );

  const filteredKeys = React.useMemo(() => {
    const query = search.trim().toLowerCase();
    const keys = Object.keys(currentValues);
    if (!query) return keys;
    return keys.filter((key) => {
      const value = currentValues[key] ?? "";
      return (
        key.toLowerCase().includes(query) || value.toLowerCase().includes(query)
      );
    });
  }, [currentValues, search]);

  const hasChanges = React.useMemo(() => {
    for (const locale of Object.keys(draftData)) {
      const current = draftData[locale] || {};
      const initial = sourceData[locale] || {};
      for (const key of Object.keys(current)) {
        if (current[key] !== initial[key]) return true;
      }
    }
    return false;
  }, [draftData, sourceData]);

  const handleValueChange = (key: string, value: string) => {
    setDraftData((prev) => ({
      ...prev,
      [activeLocale]: {
        ...(prev[activeLocale] || {}),
        [key]: value,
      },
    }));
  };

  const closeEditor = React.useCallback(() => {
    setEditorOpen(false);
    setEditorKey(null);
    setEditorTemplateValue("");
    setEditorDraftValue("");
  }, []);

  const openEditorForKey = React.useCallback(
    (key: string) => {
      if (loading || saving) return;
      const nextValue = currentValues[key] ?? "";
      setEditorKey(key);
      setEditorTemplateValue(nextValue);
      setEditorDraftValue(nextValue);
      setEditorOpen(true);
    },
    [currentValues, loading, saving],
  );

  const applyEditorChanges = React.useCallback(() => {
    if (!editorKey) return;
    handleValueChange(
      editorKey,
      joinSegmentsWithPlaceholders(
        splitTemplateSegments(editorDraftValue),
        countPlaceholders(editorTemplateValue),
      ),
    );
    closeEditor();
    toast.success("Изменение сохранено в таблице");
  }, [closeEditor, editorDraftValue, editorKey, editorTemplateValue]);

  React.useEffect(() => {
    closeEditor();
  }, [activeLocale, closeEditor]);

  const handleReset = () => {
    setDraftData(cloneLocalization(sourceData));
    closeEditor();
    toast.success("Изменения отменены");
  };

  const handleSave = async () => {
    if (!hasChanges || saving) return;
    setSaving(true);
    try {
      const updated = await localizationApi.update(draftData);
      const normalized = cloneLocalization(updated || {});
      setSourceData(normalized);
      setDraftData(cloneLocalization(normalized));
      closeEditor();
      toast.success("Локализация сохранена");
    } catch (error: any) {
      toast.error("Не удалось сохранить локализацию", {
        description: error?.message ?? "Попробуйте еще раз.",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          {!canEditLocalization ? (
            <Alert variant="destructive">
              <AlertTitle>Доступ ограничен</AlertTitle>
              <AlertDescription>
                Редактор локализации доступен только администраторам и super
                admin.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="w-full min-w-0 space-y-4">
              <div className="space-y-1">
                <h1 className="text-2xl font-semibold">Редактор локализации</h1>
                <p className="text-sm text-muted-foreground">
                  Компактный режим редактирования текстовых данных бота
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="relative min-w-[220px] max-w-md flex-1">
                  <IconSearch className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Поиск по ключу или значению"
                    className="h-9 pl-8"
                  />
                </div>

                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-9 px-3"
                  onClick={loadLocalization}
                  disabled={loading || saving}
                >
                  <IconRefresh className="h-4 w-4" />
                  Обновить
                </Button>

                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-9 px-3"
                  onClick={handleReset}
                  disabled={!hasChanges || loading || saving}
                >
                  Сбросить
                </Button>

                <Button
                  type="button"
                  size="sm"
                  className="h-9 px-3"
                  onClick={handleSave}
                  disabled={!hasChanges || loading || saving}
                >
                  <IconDeviceFloppy className="h-4 w-4" />
                  {saving ? "Сохранение..." : "Сохранить"}
                </Button>
              </div>

              {localeNames.length > 1 && (
                <div className="flex flex-wrap items-center gap-2">
                  {localeNames.map((locale) => (
                    <Button
                      key={locale}
                      type="button"
                      size="sm"
                      className="h-8 px-3"
                      variant={activeLocale === locale ? "default" : "outline"}
                      onClick={() => setActiveLocale(locale)}
                    >
                      {locale}
                    </Button>
                  ))}
                </div>
              )}

              {errorMessage ? (
                <Alert variant="destructive">
                  <AlertTitle>Ошибка</AlertTitle>
                  <AlertDescription>{errorMessage}</AlertDescription>
                </Alert>
              ) : (
                <div className="overflow-hidden rounded-md border bg-card">
                  <div className="flex min-w-max items-center justify-between gap-4 border-b px-3 py-2 text-xs font-mono text-muted-foreground">
                    <span>{activeLocale || "Локаль не выбрана"}</span>
                    <span>{filteredKeys.length} ключей</span>
                  </div>
                  <div className="max-h-[70vh] overflow-auto">
                    {loading ? (
                      <div className="px-2 py-6">
                        <Empty className="w-full border-0 py-6">
                          <EmptyHeader>
                            <EmptyMedia variant="icon">
                              <Spinner className="size-5" />
                            </EmptyMedia>
                            <EmptyTitle>Загрузка локализации</EmptyTitle>
                            <EmptyDescription>
                              Пожалуйста, подождите. Получаем данные бота.
                            </EmptyDescription>
                          </EmptyHeader>
                        </Empty>
                      </div>
                    ) : localeNames.length === 0 ? (
                      <div className="px-2 py-6">
                        <Empty className="w-full border-0 py-6">
                          <EmptyHeader>
                            <EmptyTitle>Локализация пуста</EmptyTitle>
                            <EmptyDescription>
                              Проверьте данные на стороне `bot_service`.
                            </EmptyDescription>
                          </EmptyHeader>
                        </Empty>
                      </div>
                    ) : filteredKeys.length === 0 ? (
                      <div className="px-2 py-6">
                        <Empty className="w-full border-0 py-6">
                          <EmptyHeader>
                            <EmptyMedia variant="icon">
                              <IconSearch className="size-5" />
                            </EmptyMedia>
                            <EmptyTitle>Ничего не найдено</EmptyTitle>
                            <EmptyDescription>
                              Измените поисковый запрос, чтобы увидеть ключи
                              локализации.
                            </EmptyDescription>
                          </EmptyHeader>
                        </Empty>
                      </div>
                    ) : (
                      <div className="min-w-max divide-y">
                        {filteredKeys.map((key, index) => {
                          const value = currentValues[key] ?? "";
                          const isChanged = value !== (sourceValues[key] ?? "");
                          return (
                            <div
                              key={key}
                              className={`grid min-w-max grid-cols-[28px_minmax(180px,max-content)_minmax(320px,1fr)] items-start gap-2 py-1 pl-0.5 pr-2 md:grid-cols-[32px_minmax(220px,320px)_minmax(520px,1fr)] ${
                                isChanged
                                  ? "bg-yellow-200/45 dark:bg-yellow-500/15"
                                  : ""
                              }`}
                            >
                              <div className="pt-2 pr-1 text-right font-mono text-[11px] text-muted-foreground">
                                {index + 1}
                              </div>
                              <div className="pt-2 pr-1 font-mono text-[12px] text-foreground/80">
                                "{key}"
                              </div>
                              <button
                                type="button"
                                onClick={() => openEditorForKey(key)}
                                disabled={saving || loading}
                                className="block min-w-[320px] rounded-sm px-2 py-1.5 text-left font-mono text-[13px] leading-6 text-foreground hover:bg-muted/40 disabled:cursor-not-allowed md:min-w-[520px]"
                              >
                                <span
                                  className="block whitespace-pre-wrap break-words"
                                  dangerouslySetInnerHTML={{
                                    __html: renderDisplayHtml(
                                      String(value || ""),
                                    ),
                                  }}
                                />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}

              <Sheet
                open={editorOpen}
                onOpenChange={(open) => {
                  if (!open) {
                    closeEditor();
                    return;
                  }
                  setEditorOpen(true);
                }}
              >
                <SheetContent side="right" className="w-full sm:max-w-xl p-0">
                  <SheetHeader className="border-b p-4">
                    <SheetTitle>Редактирование локализации</SheetTitle>
                    <SheetDescription>
                      Ключ: <code>{editorKey || "-"}</code>
                      {activeLocale ? (
                        <>
                          {" "}
                          · Локаль: <code>{activeLocale}</code>
                        </>
                      ) : null}
                    </SheetDescription>
                  </SheetHeader>

                  <div className="flex-1 space-y-3 overflow-auto p-4">
                    <div className="space-y-2">
                      <div className="text-xs font-medium text-muted-foreground">
                        Редактор значения
                      </div>
                      <ImmutablePlaceholderEditor
                        templateValue={editorTemplateValue}
                        value={editorDraftValue}
                        disabled={saving || loading}
                        onChange={setEditorDraftValue}
                      />
                      {countPlaceholders(editorTemplateValue) > 0 ? (
                        <p className="text-xs text-muted-foreground">
                          Плейсхолдеры <code>{PLACEHOLDER_TOKEN}</code> защищены:
                          их нельзя удалить или изменить количество.
                        </p>
                      ) : null}
                    </div>
                  </div>

                  <SheetFooter className="border-t p-4 sm:flex-row sm:justify-end">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={closeEditor}
                    >
                      Отмена
                    </Button>
                    <Button
                      type="button"
                      onClick={applyEditorChanges}
                      disabled={!editorKey}
                    >
                      Сохранить в таблице
                    </Button>
                  </SheetFooter>
                </SheetContent>
              </Sheet>
            </div>
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  );
}
