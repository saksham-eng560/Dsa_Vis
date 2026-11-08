/**
 * Monaco editor bound to the store: edits update `code`, the current dry-run
 * line is highlighted, and clicking the gutter toggles breakpoints.
 * Loaded lazily (Monaco is the largest dependency).
 */
import { useEffect, useRef } from 'react';

import { useAppStore, useCurrentStep } from '../../stores/appStore';
import type { Language } from '../../types';
import { monacoLanguage } from '../../utils/codeDetection';
import { monaco } from '../../utils/monacoSetup';

interface CodeEditorProps {
  language: Language;
}

export default function CodeEditor({ language }: CodeEditorProps) {
  const host = useRef<HTMLDivElement>(null);
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const stepDecorations = useRef<monaco.editor.IEditorDecorationsCollection | null>(null);
  const bpDecorations = useRef<monaco.editor.IEditorDecorationsCollection | null>(null);

  const theme = useAppStore((s) => s.theme);
  const breakpoints = useAppStore((s) => s.breakpoints);
  const code = useAppStore((s) => s.code);
  const currentLine = useCurrentStep()?.line ?? null;
  const showStep = useAppStore((s) => s.activeTab === 'dryrun' || s.playing);

  // Create once.
  useEffect(() => {
    if (!host.current) return;
    const editor = monaco.editor.create(host.current, {
      value: useAppStore.getState().code,
      language: monacoLanguage(language),
      theme: useAppStore.getState().theme === 'dark' ? 'codelens-dark' : 'codelens-light',
      automaticLayout: true,
      fontFamily: "'SF Mono', ui-monospace, 'JetBrains Mono', Menlo, monospace",
      fontSize: 13.5,
      lineHeight: 22,
      minimap: { enabled: false },
      glyphMargin: true,
      scrollBeyondLastLine: false,
      smoothScrolling: true,
      padding: { top: 12, bottom: 12 },
      renderLineHighlight: 'line',
      stickyScroll: { enabled: false },
      tabSize: 4,
      ariaLabel: 'Code editor. Click the gutter to toggle breakpoints.',
    });
    editorRef.current = editor;
    stepDecorations.current = editor.createDecorationsCollection();
    bpDecorations.current = editor.createDecorationsCollection();

    const sub = editor.onDidChangeModelContent(() => {
      const value = editor.getValue();
      if (value !== useAppStore.getState().code) useAppStore.getState().setCode(value);
    });
    const click = editor.onMouseDown((e) => {
      const { GUTTER_GLYPH_MARGIN, GUTTER_LINE_NUMBERS } = monaco.editor.MouseTargetType;
      if ((e.target.type === GUTTER_GLYPH_MARGIN || e.target.type === GUTTER_LINE_NUMBERS) && e.target.position) {
        useAppStore.getState().toggleBreakpoint(e.target.position.lineNumber);
      }
    });
    return () => {
      sub.dispose();
      click.dispose();
      editor.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // External code changes (presets, history, uploads, share links).
  useEffect(() => {
    const editor = editorRef.current;
    if (editor && editor.getValue() !== code) editor.setValue(code);
  }, [code]);

  useEffect(() => {
    const model = editorRef.current?.getModel();
    if (model) monaco.editor.setModelLanguage(model, monacoLanguage(language));
  }, [language]);

  useEffect(() => {
    monaco.editor.setTheme(theme === 'dark' ? 'codelens-dark' : 'codelens-light');
  }, [theme]);

  useEffect(() => {
    bpDecorations.current?.set(
      breakpoints.map((line) => ({
        range: new monaco.Range(line, 1, line, 1),
        options: { glyphMarginClassName: 'cl-breakpoint-glyph', glyphMarginHoverMessage: { value: 'Breakpoint' } },
      })),
    );
  }, [breakpoints]);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor || !showStep || currentLine == null) {
      stepDecorations.current?.clear();
      return;
    }
    stepDecorations.current?.set([
      {
        range: new monaco.Range(currentLine, 1, currentLine, 1),
        options: { isWholeLine: true, className: 'cl-current-line', glyphMarginClassName: 'cl-current-glyph' },
      },
    ]);
    editor.revealLineInCenterIfOutsideViewport(currentLine, monaco.editor.ScrollType.Smooth);
  }, [currentLine, showStep]);

  return <div ref={host} className="h-full w-full" data-testid="code-editor" />;
}
