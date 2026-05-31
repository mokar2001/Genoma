import { useDropzone } from "react-dropzone";
import { Upload, FileCode, X, CheckCircle2, FlaskConical } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  file: File | null;
  onFile: (f: File | null) => void;
  useSample: boolean;
  onUseSample: (v: boolean) => void;
}

export default function VcfUploader({ file, onFile, useSample, onUseSample }: Props) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      "text/plain": [".vcf", ".txt"],
      "application/octet-stream": [".vcf", ".gz", ".bam", ".cram", ".fastq", ".fq"],
    },
    maxFiles: 1,
    maxSize: 200 * 1024 * 1024 * 1024, // 200 GB
    disabled: useSample,
    onDropAccepted: ([f]) => onFile(f),
  });

  return (
    <div className="space-y-3">
      {/* Sample / mock toggle */}
      <label
        className={cn(
          "flex cursor-pointer items-center gap-3 rounded-xl border p-3 transition",
          useSample
            ? "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-900/20"
            : "border-slate-200 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
        )}
      >
        <input
          type="checkbox"
          checked={useSample}
          onChange={(e) => {
            onUseSample(e.target.checked);
            if (e.target.checked) onFile(null);
          }}
          className="h-4 w-4 rounded accent-amber-500"
        />
        <FlaskConical className={cn("h-5 w-5", useSample ? "text-amber-500" : "text-slate-400")} />
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
            Use sample VCF (mock run)
          </p>
          <p className="text-xs text-slate-500">
            Skip uploading — run the full pipeline on a bundled demo VCF stored on the server.
          </p>
        </div>
      </label>

      {/* When sample selected, show confirmation instead of dropzone */}
      {useSample ? (
        <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-900/20">
          <CheckCircle2 className="h-8 w-8 flex-shrink-0 text-amber-500" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-900 dark:text-white">
              Sample VCF selected
            </p>
            <p className="text-xs text-slate-500">
              The server's bundled sample variants will be analysed.
            </p>
          </div>
        </div>
      ) : file ? (
        <div className="flex items-center gap-3 rounded-xl border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20">
          <CheckCircle2 className="h-8 w-8 flex-shrink-0 text-green-500" />
          <div className="flex-1 min-w-0">
            <p className="truncate text-sm font-medium text-slate-900 dark:text-white">{file.name}</p>
            <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB · ready</p>
          </div>
          <button
            type="button"
            onClick={() => onFile(null)}
            className="rounded-lg p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30"
          >
            <X className="h-4 w-4 text-red-500" />
          </button>
        </div>
      ) : (
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
      )}
    </div>
  );
}
