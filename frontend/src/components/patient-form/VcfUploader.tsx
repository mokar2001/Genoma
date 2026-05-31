import { useDropzone } from "react-dropzone";
import { Upload, FileCode, X, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  file: File | null;
  onFile: (f: File | null) => void;
}

export default function VcfUploader({ file, onFile }: Props) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      "text/plain": [".vcf", ".txt"],
      "application/octet-stream": [".vcf", ".gz", ".bam", ".cram", ".fastq", ".fq"],
    },
    maxFiles: 1,
    maxSize: 200 * 1024 * 1024 * 1024, // 200 GB
    onDropAccepted: ([f]) => onFile(f),
  });

  if (file) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20">
        <CheckCircle2 className="h-8 w-8 flex-shrink-0 text-green-500" />
        <div className="flex-1 min-w-0">
          <p className="truncate text-sm font-medium text-slate-900 dark:text-white">{file.name}</p>
          <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB · VCF ready</p>
        </div>
        <button
          type="button"
          onClick={() => onFile(null)}
          className="rounded-lg p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30"
        >
          <X className="h-4 w-4 text-red-500" />
        </button>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition",
        isDragActive
          ? "border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20"
          : "border-slate-300 hover:border-indigo-300 hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-800"
      )}
    >
      <input {...getInputProps()} />
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg">
        {isDragActive ? (
          <FileCode className="h-7 w-7 text-white" />
        ) : (
          <Upload className="h-7 w-7 text-white" />
        )}
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          {isDragActive ? "Drop your file here" : "Upload Genomic File"}
        </p>
        <p className="text-xs text-slate-500">
          VCF · FASTQ · BAM/CRAM · Drag & drop or click · up to 200 GB
        </p>
        <p className="text-xs text-slate-400">
          FASTQ runs nf-core/sarek → VCF · VCF is used directly
        </p>
      </div>
    </div>
  );
}
