/** Client mirrors of messaging attachment defaults (server is authoritative). */

export const ATTACHMENT_ACCEPT =
  "image/jpeg,image/png,image/webp,application/pdf,text/plain,text/csv,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.jpg,.jpeg,.png,.webp,.pdf,.txt,.csv,.docx";

export const ATTACHMENT_MAX_IMAGE_BYTES = 5 * 1024 * 1024;
export const ATTACHMENT_MAX_DOC_BYTES = 10 * 1024 * 1024;
export const ATTACHMENT_MAX_TOTAL_BYTES = 15 * 1024 * 1024;
export const ATTACHMENT_MAX_COUNT = 4;

const IMAGE_TYPES = new Set([
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/webp",
]);

const ALLOWED_MIME = new Set([
  ...IMAGE_TYPES,
  "application/pdf",
  "text/plain",
  "text/csv",
  "application/csv",
  "text/x-csv",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);

const ALLOWED_EXT = new Set([
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
  ".pdf",
  ".txt",
  ".csv",
  ".docx",
]);

const BLOCKED_EXT = new Set([
  ".exe",
  ".bat",
  ".cmd",
  ".sh",
  ".js",
  ".html",
  ".htm",
  ".svg",
  ".zip",
  ".rar",
  ".7z",
  ".php",
  ".py",
  ".dll",
  ".msi",
]);

export function isImageContentType(contentType?: string | null): boolean {
  const ctype = (contentType || "").split(";")[0].trim().toLowerCase();
  return IMAGE_TYPES.has(ctype);
}

export function maxBytesForFile(file: File): number {
  return isImageContentType(file.type) || /\.(jpe?g|png|webp)$/i.test(file.name)
    ? ATTACHMENT_MAX_IMAGE_BYTES
    : ATTACHMENT_MAX_DOC_BYTES;
}

export function formatAttachmentSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileExtension(name: string): string {
  const i = name.lastIndexOf(".");
  if (i < 0) return "";
  return name.slice(i).toLowerCase();
}

/** Client-side size/type gate before REST upload (server re-validates). */
export function validateAttachmentFile(file: File): string | null {
  const ext = fileExtension(file.name);
  if (ext && BLOCKED_EXT.has(ext)) {
    return "Unsupported file type.";
  }
  if (ext && !ALLOWED_EXT.has(ext)) {
    return "Unsupported file type.";
  }
  const mime = (file.type || "").split(";")[0].trim().toLowerCase();
  if (mime && !ALLOWED_MIME.has(mime)) {
    return "Unsupported file type.";
  }
  if (!mime && !ext) {
    return "Unsupported file type.";
  }
  const limit = maxBytesForFile(file);
  if (file.size > limit) {
    return `File too large (max ${formatAttachmentSize(limit)}).`;
  }
  if (file.size <= 0) {
    return "Empty file.";
  }
  return null;
}

/** Map API / network failures to short composer-friendly copy. */
export function mapAttachmentError(err: unknown): string {
  if (err && typeof err === "object" && "status" in err) {
    const status = Number((err as { status?: number }).status);
    if (status === 403 || status === 404) {
      return "Not allowed in this thread.";
    }
  }
  const msg =
    err instanceof Error
      ? err.message
      : typeof err === "string"
        ? err
        : "Upload failed.";
  const lower = msg.toLowerCase();
  if (
    lower.includes("too large") ||
    (lower.includes("must be") && lower.includes("mb"))
  ) {
    return "File too large.";
  }
  if (
    lower.includes("not allowed") ||
    lower.includes("unsupported") ||
    lower.includes("only images") ||
    lower.includes("file type") ||
    lower.includes("does not match")
  ) {
    return "Unsupported file type.";
  }
  if (
    lower.includes("rejected") ||
    lower.includes("unsafe") ||
    lower.includes("unrecognized") ||
    lower.includes("corrupt")
  ) {
    return "Attachment rejected.";
  }
  if (
    lower.includes("not found") ||
    lower.includes("participant") ||
    lower.includes("cannot reply") ||
    lower.includes("blocked") ||
    lower.includes("forbidden")
  ) {
    return "Not allowed in this thread.";
  }
  if (lower.includes("upload") || lower.includes("failed") || lower.includes("network")) {
    return "Upload failed.";
  }
  return msg.length > 120 ? "Upload failed." : msg;
}

export function isPdfContentType(contentType?: string | null): boolean {
  return (contentType || "").split(";")[0].trim().toLowerCase() === "application/pdf";
}

export function documentKindLabel(contentType?: string | null): string {
  const ctype = (contentType || "").split(";")[0].trim().toLowerCase();
  if (ctype === "application/pdf") return "PDF";
  if (ctype === "text/csv" || ctype === "application/csv") return "CSV";
  if (ctype.includes("wordprocessingml") || ctype.includes("docx")) return "DOCX";
  if (ctype === "text/plain") return "Text";
  if (isImageContentType(ctype)) return "Image";
  return "File";
}
