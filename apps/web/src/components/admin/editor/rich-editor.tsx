"use client";

import { CKEditor } from "@ckeditor/ckeditor5-react";
import {
  Autoformat,
  AutoLink,
  BlockQuote,
  Bold,
  ClassicEditor,
  Code,
  CodeBlock,
  type Editor,
  Essentials,
  type FileLoader,
  GeneralHtmlSupport,
  Heading,
  HorizontalLine,
  Image,
  ImageCaption,
  ImageInsert,
  ImageStyle,
  ImageTextAlternative,
  ImageToolbar,
  ImageUpload,
  Italic,
  Link,
  LinkImage,
  List,
  Paragraph,
  PasteFromOffice,
  Strikethrough,
  Table,
  TableToolbar,
  Underline,
  type UploadAdapter,
  type UploadResponse,
} from "ckeditor5";
import { useImperativeHandle, useRef, type Ref } from "react";

import "ckeditor5/ckeditor5.css";

import { uploadImage } from "@/lib/upload";

export interface RichEditorHandle {
  getHtml: () => string;
  insertImage: (params: { src: string; alt: string }) => void;
}

/**
 * CKEditor → Cloudinary upload adapter.
 *
 * The editor hands us a `FileLoader` exposing the picked file. We feed it
 * through `uploadImage()` (signed Cloudinary upload + persisted media row)
 * and return the resulting `secure_url` in the shape CKEditor expects.
 *
 * Alt text: CKEditor doesn't prompt during upload, so we seed from the
 * filename. The user can refine via the image toolbar's "Change image text
 * alternative" button afterwards - only the rendered `<img alt>` matters for
 * the public site; the media row's alt is just a default we picked.
 */
class CloudinaryUploadAdapter implements UploadAdapter {
  constructor(private readonly loader: FileLoader) {}

  async upload(): Promise<UploadResponse> {
    const file = await this.loader.file;
    if (!file) {
      throw new Error("No file provided to upload adapter.");
    }
    const altGuess =
      (file.name || "image").replace(/\.[^.]+$/, "").trim() || "Image";
    const media = await uploadImage({
      file,
      alt: altGuess,
      folder: "posts/inline",
    });
    return { default: media.secure_url };
  }

  abort(): void {
    // `uploadImage` is fire-and-forget at the network layer; nothing to cancel.
    // CKEditor handles the placeholder cleanup on its own when the promise
    // rejects or this method is called.
  }
}

// Typed against the base `Editor` - that's what CKEditor's `extraPlugins`
// `PluginConstructor` contract expects; `FileRepository` lives on every editor.
function CloudinaryUploadAdapterPlugin(editor: Editor): void {
  editor.plugins.get("FileRepository").createUploadAdapter = (loader) =>
    new CloudinaryUploadAdapter(loader);
}

interface Props {
  initialHtml: string;
  onChange: () => void;
  editorRef?: Ref<RichEditorHandle>;
}

/**
 * CKEditor 5 ClassicEditor configured for blog post writing.
 *
 * Output is HTML. The server (app/services/posts.update_post_content) runs the
 * HTML through nh3 sanitisation before persisting, so we don't strictly need
 * to constrain the editor's plugin set on safety grounds - but a tighter
 * toolbar makes for a calmer writing experience anyway.
 *
 * License: declared as "GPL" - the GPL-2.0 build is free for OSS / personal
 * use. Swap to a paid licenseKey before any commercial deployment.
 */
export function RichEditor({ initialHtml, onChange, editorRef }: Props) {
  const instanceRef = useRef<ClassicEditor | null>(null);

  useImperativeHandle(
    editorRef,
    () => ({
      getHtml: () => instanceRef.current?.getData() ?? "",
      insertImage: ({ src, alt }) => {
        const editor = instanceRef.current;
        if (!editor) return;
        editor.execute("insertImage", { source: [{ src, alt }] });
      },
    }),
    [],
  );

  return (
    <div className="rich-editor rounded-md border border-border bg-bg-elevated">
      <CKEditor
        editor={ClassicEditor}
        data={initialHtml || ""}
        config={{
          licenseKey: "GPL",
          plugins: [
            Essentials,
            Paragraph,
            Heading,
            Bold,
            Italic,
            Underline,
            Strikethrough,
            Code,
            CodeBlock,
            Link,
            AutoLink,
            List,
            BlockQuote,
            HorizontalLine,
            Image,
            ImageCaption,
            ImageStyle,
            ImageToolbar,
            ImageInsert,
            ImageUpload,
            ImageTextAlternative,
            LinkImage,
            Table,
            TableToolbar,
            Autoformat,
            PasteFromOffice,
            // Permits id/class on a few elements so the sanitiser-allowed
            // syntax-highlight class names survive the editor round-trip.
            GeneralHtmlSupport,
          ],
          extraPlugins: [CloudinaryUploadAdapterPlugin],
          toolbar: {
            items: [
              "heading",
              "|",
              "bold",
              "italic",
              "underline",
              "strikethrough",
              "code",
              "link",
              "|",
              "bulletedList",
              "numberedList",
              "blockQuote",
              "codeBlock",
              "horizontalLine",
              "|",
              "insertImage",
              "insertTable",
              "|",
              "undo",
              "redo",
            ],
            shouldNotGroupWhenFull: false,
          },
          heading: {
            options: [
              { model: "paragraph", title: "Paragraph", class: "ck-heading_paragraph" },
              { model: "heading2", view: "h2", title: "Heading 2", class: "ck-heading_heading2" },
              { model: "heading3", view: "h3", title: "Heading 3", class: "ck-heading_heading3" },
              { model: "heading4", view: "h4", title: "Heading 4", class: "ck-heading_heading4" },
            ],
          },
          link: {
            defaultProtocol: "https://",
            addTargetToExternalLinks: true,
          },
          image: {
            toolbar: [
              "imageStyle:inline",
              "imageStyle:block",
              "imageStyle:side",
              "|",
              "toggleImageCaption",
              "imageTextAlternative",
              "linkImage",
            ],
          },
          table: {
            contentToolbar: ["tableColumn", "tableRow", "mergeTableCells"],
          },
          htmlSupport: {
            allow: [
              { name: "code", attributes: { class: true } },
              { name: "pre", attributes: { class: true } },
            ],
          },
        }}
        onReady={(editor) => {
          instanceRef.current = editor;
        }}
        onChange={() => onChange()}
        onError={(error, { willEditorRestart }) => {
          // eslint-disable-next-line no-console
          console.error("CKEditor error:", error, { willEditorRestart });
        }}
      />
    </div>
  );
}
