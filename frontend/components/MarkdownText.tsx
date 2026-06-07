import { Markdown } from "markdown-to-jsx";

interface MarkdownTextProps {
  content: string;
  className?: string;
}

const HeadingStyle = (level: string) => ({
  h1: "text-2xl font-semibold mt-3 mb-1",
  h2: "text-xl font-semibold mt-2 mb-1",
  h3: "text-lg font-semibold mt-2 mb-0.5",
  h4: "font-semibold mt-1 mb-0.5",
  h5: "font-semibold mt-1 mb-0.5",
  h6: "font-semibold mt-1 mb-0.5",
}[level] || "");

export function MarkdownText({ content, className = "" }: MarkdownTextProps) {
  const options = {
    overrides: {
      h1: ({ children }: any) => (
        <h1 className="text-2xl font-semibold mt-3 mb-1 text-[#f5f5f5]">{children}</h1>
      ),
      h2: ({ children }: any) => (
        <h2 className="text-xl font-semibold mt-2 mb-1 text-[#f5f5f5]">{children}</h2>
      ),
      h3: ({ children }: any) => (
        <h3 className="text-lg font-semibold mt-2 mb-0.5 text-[#f5f5f5]">{children}</h3>
      ),
      h4: ({ children }: any) => (
        <h4 className="font-semibold mt-1 mb-0.5 text-[#f5f5f5]">{children}</h4>
      ),
      h5: ({ children }: any) => (
        <h5 className="font-semibold mt-1 mb-0.5 text-[#f5f5f5]">{children}</h5>
      ),
      h6: ({ children }: any) => (
        <h6 className="font-semibold mt-1 mb-0.5 text-[#f5f5f5]">{children}</h6>
      ),
      p: ({ children }: any) => (
        <p className="mb-2 text-[#f5f5f5]">{children}</p>
      ),
      ul: ({ children }: any) => (
        <ul className="list-disc list-inside mb-2 ml-2 mt-0 text-[#f5f5f5]">{children}</ul>
      ),
      ol: ({ children }: any) => (
        <ol className="list-decimal list-inside mb-2 ml-2 mt-0 text-[#f5f5f5]">{children}</ol>
      ),
      li: ({ children }: any) => (
        <li className="mb-0.5 text-[#f5f5f5]">{children}</li>
      ),
      code: ({ children, className: codeClassName }: any) => {
        if (codeClassName?.includes("hljs") || codeClassName?.includes("language-")) {
          return (
            <code className="block bg-[#1a1a1a] text-[#a0a0a0] p-3 rounded-lg mb-2 text-xs font-mono overflow-x-auto border border-[#2a2a2a]">
              {children}
            </code>
          );
        }
        return (
          <code className="bg-[#2a2a2a] text-[#d97706] px-2 py-0.5 rounded text-xs font-mono">
            {children}
          </code>
        );
      },
      pre: ({ children }: any) => (
        <pre className="bg-[#1a1a1a] p-3 rounded-lg mb-2 overflow-x-auto border border-[#2a2a2a]">
          {children}
        </pre>
      ),
      blockquote: ({ children }: any) => (
        <blockquote className="border-l-4 border-[#d97706] bg-[#1a1a1a] pl-3 py-2 my-2 text-[#a0a0a0]">
          {children}
        </blockquote>
      ),
      a: ({ children, ...props }: any) => (
        <a
          className="text-[#d97706] hover:text-[#b45309] underline transition-colors"
          target="_blank"
          rel="noopener noreferrer"
          {...props}
        >
          {children}
        </a>
      ),
      hr: () => <hr className="my-4 border-[#2a2a2a]" />,
      strong: ({ children }: any) => (
        <strong className="font-bold text-[#d97706]">{children}</strong>
      ),
      em: ({ children }: any) => (
        <em className="italic text-[#a0a0a0]">{children}</em>
      ),
    } as any,
  };

  return (
    <div className={`text-[#f5f5f5] leading-relaxed ${className}`}>
      <Markdown options={options}>{content}</Markdown>
    </div>
  );
}
