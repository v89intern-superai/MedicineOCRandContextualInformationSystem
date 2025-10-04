import React, { useState } from "react";
import type { ChangeEvent } from "react";
import ReactMarkdown from "react-markdown";

const ImageUploader: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState("No file chosen");
  const [extractedText, setExtractedText] = useState<string>("");
  const [ragText, setRagText] = useState<string>("");
  const [previewUrl, setPreviewUrl] = useState<string>("../img/image-1@2x.jpg");

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setFileName(selectedFile.name);
      setPreviewUrl(URL.createObjectURL(selectedFile)); // immediate preview
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    setExtractedText("Processing...");
    setRagText("");

    try {
      // Step 1: Call OCR endpoint
      const ocrRes = await fetch("http://localhost:5000/ocr", {
        method: "POST",
        body: formData,
      });

      if (!ocrRes.ok) {
        const text = await ocrRes.text();
        console.error("OCR error:", text);
        setExtractedText("Error uploading file");
        return;
      }

      const ocrData = await ocrRes.json();
      const text = ocrData.ocr_text || "No text found";
      setExtractedText(text);

      // Step 2: Call RAG endpoint only if OCR text is not empty
      if (text && text !== "No text found") {
        setRagText("Processing...");
        const ragRes = await fetch("http://localhost:5000/rag", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ocr_text: text }),
        });

        if (!ragRes.ok) {
          const ragText = await ragRes.text();
          console.error("RAG error:", ragText);
          setRagText("Error fetching RAG");
          return;
        }

        const ragData = await ragRes.json();
        setRagText(ragData.llm_text || "No text found");
      }
    } catch (err) {
      console.error(err);
      setExtractedText("Error uploading file");
      setRagText("Error uploading file");
    }
  };

  return (
    <div className="flex flex-col w-screen h-screen items-center justify-center gap-5">
      <span className="text-5xl font-bold mb-4 text-center">
        Medicine OCR and Contextual Information System
      </span>
      <div className="flex w-full h-[80%] items-center justify-center gap-10 px-10">
        {/* Left: Image + Upload */}
        <div className="flex flex-col w-1/2 h-full justify-between pb-10 gap-8">
          <div className="flex justify-center h-full bg-neutral-900 rounded-lg overflow-auto">
            {previewUrl && (
              <img
                src={previewUrl}
                alt="Uploaded"
                className="object-contain max-h-full"
              />
            )}
          </div>
          <div className="flex flex-col items-center gap-4">
            <div className="flex items-center w-full">
              <input
                type="file"
                id="file-upload"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer bg-[#1a1a1a] text-white text-xl font-semibold px-4 py-2 rounded-lg border border-transparent hover:border-[#646cff] duration-250"
              >
                Choose File
              </label>
              <span className="px-4 text-lg text-white">{fileName}</span>
            </div>
            <button
              onClick={handleUpload}
              disabled={!file || extractedText == "Processing"}
              className={`w-full text-xl font-bold px-4 py-4 rounded-2xl border border-transparent ${
                !file || extractedText == "Processing..."
                  ? "bg-neutral-700 text-neutral-500 cursor-not-allowed"
                  : "bg-[#1a1a1a] text-white hover:border-[#646cff] duration-250"
              }`}
            >
              {extractedText == "Processing" ? "Processing..." : "Process"}
            </button>
          </div>
        </div>

        {/* Right: Markdown display*/}
        {extractedText && extractedText !== "" && (
          <div className="flex w-2/5 h-full pb-10 px-5">
            <div className="flex flex-col justify-start w-full h-full gap-10">
              {extractedText.startsWith("Error") ? (
                <div className="text-red-500 text-xl">{extractedText}</div>
              ) : (
                <>
                  <div
                    className={`flex flex-col overflow-auto ${
                      ragText == "" ? "" : "max-h-[45%]"
                    }`}
                  >
                    <div className="text-3xl font-bold mb-5">
                      Extracted Text
                    </div>
                    <div className="px-9 py-5 bg-neutral-700 rounded-lg overflow-auto">
                      <ReactMarkdown>{extractedText}</ReactMarkdown>
                    </div>
                  </div>
                  <div className="flex flex-col max-h-[45%] overflow-auto">
                    {ragText && ragText !== "" && (
                      <>
                        <div className="text-3xl font-bold mb-5">
                          From Database
                        </div>
                        <div className="px-9 py-5 bg-neutral-700 rounded-lg overflow-auto">
                          <ReactMarkdown>{ragText}</ReactMarkdown>
                        </div>
                      </>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ImageUploader;
