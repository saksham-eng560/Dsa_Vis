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

monaco.editor.defineTheme('codelens-dark', {
  base: 'vs-dark',
  inherit: true,
  rules: [
    { token: 'keyword', foreground: 'c4b5fd' },
    { token: 'string', foreground: '6ee7b7' },
    { token: 'number', foreground: 'fbbf24' },
    { token: 'comment', foreground: '6b7299', fontStyle: 'italic' },
  ],
  colors: { ...shared, 'editorLineNumber.foreground': '#4b5180', 'editor.lineHighlightBackground': '#ffffff08' },
});

monaco.editor.defineTheme('codelens-light', {
  base: 'vs',
  inherit: true,
  rules: [{ token: 'keyword', foreground: '6d28d9' }, { token: 'comment', foreground: '8a8fb5', fontStyle: 'italic' }],
  colors: { ...shared, 'editorLineNumber.foreground': '#a5a9cf', 'editor.lineHighlightBackground': '#6366f10a' },
});

export { monaco };
