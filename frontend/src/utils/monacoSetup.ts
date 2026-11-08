/**
 * Monaco bootstrap: bundle the core editor locally (no CDN) with syntax
 * highlighting for the supported languages only. Heavy language services
 * (TS checker, JSON, CSS) are deliberately excluded to keep the chunk small.
 */
import * as monaco from 'monaco-editor/editor/editor.api';
import EditorWorker from 'monaco-editor/editor/editor.worker?worker';
import 'monaco-editor/features/register.all';
import 'monaco-editor/languages/definitions/cpp/register';
import 'monaco-editor/languages/definitions/go/register';
import 'monaco-editor/languages/definitions/java/register';
import 'monaco-editor/languages/definitions/javascript/register';
import 'monaco-editor/languages/definitions/python/register';
import 'monaco-editor/languages/definitions/rust/register';
import 'monaco-editor/languages/definitions/typescript/register';

self.MonacoEnvironment = { getWorker: () => new EditorWorker() };

const shared = { 'editor.background': '#00000000', 'editorGutter.background': '#00000000' };

// Xcode-inspired palettes (default dark / light).
monaco.editor.defineTheme('codelens-dark', {
  base: 'vs-dark',
  inherit: true,
  rules: [
    { token: 'keyword', foreground: 'ff7ab2', fontStyle: 'bold' },
    { token: 'string', foreground: 'ff8170' },
    { token: 'number', foreground: 'd9c97c' },
    { token: 'comment', foreground: '7f8c98', fontStyle: 'italic' },
    { token: 'type', foreground: 'dabaff' },
    { token: 'identifier', foreground: 'ffffff' },
    { token: 'delimiter', foreground: 'a1a1a6' },
  ],
  colors: {
    ...shared,
    'editor.foreground': '#f5f5f7',
    'editorLineNumber.foreground': '#4e4e53',
    'editorLineNumber.activeForeground': '#a1a1a6',
    'editor.lineHighlightBackground': '#ffffff07',
    'editor.selectionBackground': '#0a84ff40',
    'editorCursor.foreground': '#0a84ff',
    'editorIndentGuide.background1': '#ffffff10',
  },
});

monaco.editor.defineTheme('codelens-light', {
  base: 'vs',
  inherit: true,
  rules: [
    { token: 'keyword', foreground: 'ad3da4', fontStyle: 'bold' },
    { token: 'string', foreground: 'd12f1b' },
    { token: 'number', foreground: '272ad8' },
    { token: 'comment', foreground: '707f8c', fontStyle: 'italic' },
    { token: 'type', foreground: '703daa' },
  ],
  colors: {
    ...shared,
    'editorLineNumber.foreground': '#b4b4b9',
    'editor.lineHighlightBackground': '#0071e308',
    'editor.selectionBackground': '#0071e330',
    'editorCursor.foreground': '#0071e3',
  },
});

export { monaco };
