// File parser utilities: CSV, XLSX, PDF, TXT → raw text for extraction pipeline
import * as XLSX from 'xlsx';
import type { GlobalWorkerOptions } from 'pdfjs-dist';
// NOTE: pdfjs-dist needs a workerSrc for browser rendering; for text extraction we use the raw API.

export type ParsedFileResult = {
    text: string;
    filename: string;
    rowCount?: number;
    error?: string;
};

/** Read CSV or plain text directly */
function readAsText(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = e => resolve((e.target?.result as string) ?? '');
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsText(file);
    });
}

/** Parse XLSX / XLS / ODS into CSV-ish text */
async function parseSpreadsheet(file: File): Promise<string> {
    const buf = await file.arrayBuffer();
    const wb = XLSX.read(buf, { type: 'array' });
    const lines: string[] = [];
    wb.SheetNames.forEach(name => {
        const ws = wb.Sheets[name];
        const csv = XLSX.utils.sheet_to_csv(ws, { strip: true });
        if (csv.trim()) lines.push(csv);
    });
    return lines.join('\n');
}

/** Extract text from a PDF using pdfjs-dist */
async function parsePDF(file: File): Promise<string> {
    // Lazy-import so webpack/vite doesn't bundle it unless needed
    const pdfjsLib = await import('pdfjs-dist');
    // Use the bundled worker shipped with pdfjs-dist >= 4.x
    pdfjsLib.GlobalWorkerOptions.workerSrc =
        new URL('pdfjs-dist/build/pdf.worker.mjs', import.meta.url).toString();

    const buf = await file.arrayBuffer();
    const doc = await pdfjsLib.getDocument({ data: buf }).promise;
    const parts: string[] = [];
    for (let p = 1; p <= doc.numPages; p++) {
        const page = await doc.getPage(p);
        const content = await page.getTextContent();
        const items = content.items.map((i: any) => i.str).join(' ');
        parts.push(items);
    }
    return parts.join('\n');
}

export async function parseFile(file: File): Promise<ParsedFileResult> {
    const name = file.name.toLowerCase();
    try {
        let text = '';
        if (name.endsWith('.pdf')) {
            text = await parsePDF(file);
        } else if (
            name.endsWith('.xlsx') ||
            name.endsWith('.xls') ||
            name.endsWith('.ods') ||
            name.endsWith('.numbers')
        ) {
            text = await parseSpreadsheet(file);
        } else {
            // CSV, TSV, TXT, or any other text-based format
            text = await readAsText(file);
        }
        const rowCount = text.split('\n').filter(l => l.trim()).length;
        return { text, filename: file.name, rowCount };
    } catch (e: any) {
        return { text: '', filename: file.name, error: e.message };
    }
}
