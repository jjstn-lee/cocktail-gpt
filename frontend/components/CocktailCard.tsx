interface Cocktail {
  name: string;
  ingredients: string[];
  method: string;
  flavor_notes: string[];
  why_this_works: string;
  match_percentage?: number;
}

interface CocktailCardProps {
  cocktail: Cocktail;
  index: number;
}

export function CocktailCard({ cocktail, index }: CocktailCardProps) {
  return (
    <div
      className="group border border-[#2a2a2a] rounded-xl p-5 hover:border-[#d97706] hover:bg-[#1a1a1a] transition-all duration-300 cursor-pointer animate-in fade-in slide-in-from-left-4 duration-300"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className="flex items-start justify-between gap-4 mb-3">
        <h3 className="text-lg font-semibold text-[#f5f5f5] group-hover:text-[#d97706] transition-colors">
          {cocktail.name}
        </h3>
        <div className="flex items-center gap-2">
          {cocktail.match_percentage !== undefined && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#d97706]/10 border border-[#d97706]/30">
              <div className="w-1.5 h-1.5 rounded-full bg-[#d97706]"></div>
              <span className="text-xs font-semibold text-[#d97706]">
                {(cocktail.match_percentage * 100).toFixed(0)}%
              </span>
            </div>
          )}
          <span className="text-sm font-medium text-[#d97706]">
            #{index + 1}
          </span>
        </div>
      </div>

      <div className="space-y-3 text-sm">
        <div className="pb-2 border-b border-[#2a2a2a]">
          <p className="text-[#d97706] italic text-base">
            "{cocktail.why_this_works}"
          </p>
        </div>

        <div>
          <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
            Ingredients
          </p>
          <p className="text-[#a0a0a0]">
            {cocktail.ingredients.join(" • ")}
          </p>
        </div>

        <div className="h-px bg-[#2a2a2a]"></div>

        <div>
          <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
            Method
          </p>
          <p className="text-[#a0a0a0]">{cocktail.method}</p>
        </div>

        <div>
          <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
            Flavor Notes
          </p>
          <div className="flex gap-2 flex-wrap">
            {cocktail.flavor_notes.map((note: string) => (
              <span
                key={note}
                className="px-3 py-1 bg-[#2a2a2a] text-[#a0a0a0] rounded-full text-xs"
              >
                {note}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
