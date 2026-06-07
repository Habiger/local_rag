export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
}

export interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string; // e.g., "root/finance/q1_report.pdf"
  children?: FileNode[];
}