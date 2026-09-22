-- Pandoc Lua filter for reports/final/AETHER_paper.md -> LaTeX (XeTeX via tectonic).
--
-- What it does, and nothing else:
--   * drops the markdown title line, the author line and the horizontal rules
--     (the title block is paper_build/titlepage.tex);
--   * turns the "Draft status" paragraph into the page-1 banner box;
--   * strips the hand-typed "N." / "N.N" prefixes from headings so LaTeX numbers them
--     (the numbers are checked to agree, so every "§N.N" in the text still resolves);
--   * converts "![Figure N](path)" + "*Figure N. caption*" pairs into real figures,
--     swapping the PNG for the sibling vector PDF where one exists, and checks that the
--     hand-typed figure numbers match the order they are typeset in;
--   * converts "**Table N. caption**" + pipe table into a captioned booktabs table, sizing the
--     columns from their content so nothing overflows the text block;
--   * maps glyphs the body face (Charter) lacks: superscript/subscript digits become
--     \textsuperscript / \textsubscript, primes and arrows go to STIX Two Math, the
--     reference-tier emoji become coloured Zapf Dingbats marks, q with a combining
--     dot above becomes \.{q};
--   * lets long file paths and run IDs in code spans break at / _ - .
-- It never changes a word of prose.

local stringify = pandoc.utils.stringify

-- ---------------------------------------------------------------- glyph mapping
local SUP = {
  ["⁰"]="0", ["¹"]="1", ["²"]="2", ["³"]="3", ["⁴"]="4", ["⁵"]="5",
  ["⁶"]="6", ["⁷"]="7", ["⁸"]="8", ["⁹"]="9", ["⁻"]="−", ["ᐟ"]="/",
}
local SUB = {
  ["₀"]="0", ["₁"]="1", ["₂"]="2", ["₃"]="3", ["₄"]="4", ["₅"]="5",
  ["₆"]="6", ["₇"]="7", ["₈"]="8", ["₉"]="9",
}
local SYM = { ["′"]=true, ["″"]=true, ["→"]=true }          -- not in Charter
local MARK = { ["✅"]="\\tierok{}", ["🟡"]="\\tiermid{}", ["❌"]="\\tierno{}" }
local DOT_ABOVE = "\u{0307}"

local function utf8chars(s)
  local out = {}
  for _, c in utf8.codes(s) do out[#out+1] = utf8.char(c) end
  return out
end

local function latex_escape(s)
  return (s:gsub("[\\{}%$&#%%_^~]", {
    ["\\"]="\\textbackslash{}", ["{"]="\\{", ["}"]="\\}", ["$"]="\\$", ["&"]="\\&",
    ["#"]="\\#", ["%"]="\\%", ["_"]="\\_", ["^"]="\\^{}", ["~"]="\\~{}" }))
end

-- Split one Str into Str / RawInline pieces.
local function map_str(s)
  local chars = utf8chars(s)
  local out, buf = {}, {}
  local function flush()
    if #buf > 0 then out[#out+1] = pandoc.Str(table.concat(buf)); buf = {} end
  end
  local i = 1
  while i <= #chars do
    local c = chars[i]
    if SUP[c] then
      flush()
      local run = {}
      while i <= #chars and SUP[chars[i]] do run[#run+1] = SUP[chars[i]]; i = i + 1 end
      out[#out+1] = pandoc.RawInline("latex", "\\textsuperscript{" .. table.concat(run) .. "}")
    elseif SUB[c] then
      flush()
      local run = {}
      while i <= #chars and SUB[chars[i]] do run[#run+1] = SUB[chars[i]]; i = i + 1 end
      out[#out+1] = pandoc.RawInline("latex", "\\textsubscript{" .. table.concat(run) .. "}")
    elseif SYM[c] then
      flush()
      out[#out+1] = pandoc.RawInline("latex", "{\\symfont " .. c .. "}")
      i = i + 1
    elseif MARK[c] then
      flush()
      out[#out+1] = pandoc.RawInline("latex", MARK[c])
      i = i + 1
    elseif c == DOT_ABOVE then
      local base = table.remove(buf)
      flush()
      out[#out+1] = pandoc.RawInline("latex", "\\.{" .. (base or "") .. "}")
      i = i + 1
    else
      buf[#buf+1] = c
      i = i + 1
    end
  end
  flush()
  -- long slash-separated tokens (URLs in the reference list) may break after "/"
  for k, v in ipairs(out) do
    if v.t == "Str" and #v.text > 28 and v.text:find("/", 1, true) then
      out[k] = pandoc.RawInline("latex", (latex_escape(v.text):gsub("/", "/\\allowbreak{}")))
    end
  end
  return out
end

local function Str(el)
  local pieces = map_str(el.text)
  if #pieces == 1 and pieces[1].t == "Str" then return nil end
  return pieces
end

-- code spans: run IDs and file paths; allow breaks at / _ -
local function Code(el)
  local s = latex_escape(el.text)
  s = s:gsub("\\_", "\\_\\allowbreak{}"):gsub("/", "/\\allowbreak{}"):gsub("%-", "-\\allowbreak{}")
  return pandoc.RawInline("latex", "\\texttt{" .. s .. "}")
end

-- ---------------------------------------------------------------- helpers
local inline_map = { Str = Str, Code = Code }
local function inlines_to_latex(inl)
  local mapped = pandoc.Inlines(inl):walk(inline_map)
  return pandoc.write(pandoc.Pandoc({ pandoc.Plain(mapped) }), "latex")
end

local function drop_first(inl, n)
  local out = pandoc.List()
  for i = n + 1, #inl do out[#out+1] = inl[i] end
  return out
end

-- figure geometry: read the PDF page box to decide how tall a figure may be
local function pdf_aspect(path)
  local h = io.popen('pdfinfo "' .. path .. '" 2>/dev/null')
  if not h then return nil end
  local txt = h:read("*a"); h:close()
  local w, ht = txt:match("Page size:%s+([%d%.]+) x ([%d%.]+)")
  if w and ht then return tonumber(w) / tonumber(ht) end
  return nil
end

local expect_fig = 1
local in_appendix = false
local fig_count_body, fig_count_appendix = 0, 0

local function make_figure(img, cap_inlines)
  local src = img.src
  if not src:match("^/") then
    src = pandoc.path.normalize(pandoc.path.join({ pandoc.system.get_working_directory(), src }))
  end
  local pdf = src:gsub("%.png$", ".pdf")
  local f = io.open(pdf, "r")
  local path = src
  if f then f:close(); path = pdf end
  local ar = pdf_aspect(path) or 1.5
  -- height caps: tall four-panels and the design grid / squarish plots / wide plots.
  -- The appendix gallery is packed tighter so two figures can share a page.
  local tall, mid, wide = 0.70, 0.46, 0.42
  if in_appendix then tall, mid, wide = 0.66, 0.34, 0.28 end
  local cap = (ar < 0.85) and tall or (ar < 1.35) and mid or wide
  local size = ("width=\\linewidth,height=%.2f\\textheight,keepaspectratio"):format(cap)
  local cap = inlines_to_latex(cap_inlines)
  return pandoc.RawBlock("latex", table.concat({
    "\\begin{figure}[htbp]", "\\centering",
    "\\includegraphics[" .. size .. "]{" .. path .. "}",
    "\\caption{" .. cap .. "}", "\\end{figure}" }, "\n"))
end

-- table column widths from content: longest cell per column, floored, normalised
local function size_table(tbl)
  local ncol = #tbl.colspecs
  local maxlen, maxtok = {}, {}
  for c = 1, ncol do maxlen[c] = 1; maxtok[c] = 1 end
  local function scan(rows)
    for _, row in ipairs(rows) do
      for c, cell in ipairs(row.cells) do
        local txt = stringify(cell.contents)
        if #txt > maxlen[c] then maxlen[c] = #txt end
        for tok in txt:gmatch("%S+") do
          if #tok > maxtok[c] then maxtok[c] = #tok end
        end
      end
    end
  end
  scan(tbl.head.rows)
  for _, body in ipairs(tbl.bodies) do scan(body.body) end
  local total = 0
  for c = 1, ncol do total = total + maxlen[c] end
  if total <= 95 and ncol <= 5 then return tbl end     -- fits naturally; keep auto columns
  local widths, sum = {}, 0
  for c = 1, ncol do
    -- damp very long cells so one wordy column does not starve the numeric ones
    -- never narrower than the column's longest single word (its header, usually)
    widths[c] = math.max(maxtok[c] + 3, 8, math.min(maxlen[c], 45))
    sum = sum + widths[c]
  end
  for c = 1, ncol do
    tbl.colspecs[c] = { tbl.colspecs[c][1], widths[c] / sum }
  end
  return tbl
end


-- Render a table as a booktabs tabular. pandoc's longtable is avoided on purpose: whenever a
-- top float lands on the page a longtable starts on, longtable mis-measures the remaining room
-- and the page overruns its bottom margin by the float's height.
local function cell_tex(cell)
  local inl = pandoc.List()
  for _, b in ipairs(cell.contents) do
    if b.t == "Plain" or b.t == "Para" then inl:extend(b.content) end
  end
  return inlines_to_latex(inl)
end

local function render_table(tbl, caption_inlines)
  local ncol = #tbl.colspecs
  local spec = {}
  for c = 1, ncol do
    local w = tbl.colspecs[c][2]
    if w and w > 0 then
      spec[#spec+1] = (">{\\raggedright\\arraybackslash}p{\\dimexpr(\\linewidth-%d\\tabcolsep)*%d/1000\\relax}")
                      :format(2 * ncol, math.floor(w * 1000))
    else
      spec[#spec+1] = "l"
    end
  end
  local lines = {}
  local fs = (ncol >= 7) and "\\footnotesize" or "\\small"
  if caption_inlines then
    lines[#lines+1] = "\\begin{table}[htbp]"
    lines[#lines+1] = "\\caption{" .. inlines_to_latex(caption_inlines) .. "}"
  else
    lines[#lines+1] = "\\begin{center}"
  end
  lines[#lines+1] = fs .. "\\centering"
  lines[#lines+1] = "\\begin{tabular}{@{}" .. table.concat(spec) .. "@{}}"
  lines[#lines+1] = "\\toprule"
  for _, row in ipairs(tbl.head.rows) do
    local cells = {}
    for _, cell in ipairs(row.cells) do
      local t = cell_tex(cell)
      cells[#cells+1] = (t ~= "") and ("\\tabhead{" .. t .. "}") or ""
    end
    lines[#lines+1] = table.concat(cells, " & ") .. " \\\\"
  end
  lines[#lines+1] = "\\midrule"
  for _, body in ipairs(tbl.bodies) do
    for _, row in ipairs(body.body) do
      local cells = {}
      for _, cell in ipairs(row.cells) do cells[#cells+1] = cell_tex(cell) end
      lines[#lines+1] = table.concat(cells, " & ") .. " \\\\"
    end
  end
  lines[#lines+1] = "\\bottomrule"
  lines[#lines+1] = "\\end{tabular}"
  lines[#lines+1] = caption_inlines and "\\end{table}" or "\\end{center}"
  return pandoc.RawBlock("latex", table.concat(lines, "\n"))
end


-- ---------------------------------------------------------------- headers
-- NB: --shift-heading-level-by is applied after filters, so "##" arrives as level 2 here.
local function Header(el)
  if el.level == 1 then return {} end          -- the markdown title; titlepage.tex carries it
  local txt = stringify(el.content)
  if el.level == 2 then
    local app, rest = txt:match("^Appendix (%a)%. (.+)$")
    if app then
      local h = pandoc.Header(2, pandoc.read(rest, "markdown").blocks[1].content)
      return { pandoc.RawBlock("latex", "\\clearpage\\appendix\\renewcommand{\\thefigure}{A.\\arabic{figure}}\\setcounter{figure}{0}"), h }
    end
    local n = txt:match("^(%d+)%. ")
    if n then
      -- drop "N." and the following space
      local inl = drop_first(el.content, 2)
      local h = pandoc.Header(2, inl)
      if n == "2" then
        return { pandoc.RawBlock("latex", "\\tableofcontents\\clearpage"), h }
      elseif n == "20" then
        return { pandoc.RawBlock("latex", "\\FloatBarrier"), h }
      end
      return h
    end
  elseif el.level == 3 then
    if txt:match("^%d+%.%d+ ") then
      return pandoc.Header(3, drop_first(el.content, 2))
    end
    el.classes:insert("unnumbered")
    return el
  end
  return el
end

-- ---------------------------------------------------------------- block pairs
local function Blocks(blocks)
  local out = pandoc.List()
  local i = 1
  while i <= #blocks do
    local b = blocks[i]
    local nxt = blocks[i + 1]
    -- figure: Para[Image] followed by Para[Emph "Figure N. ..."]
    if b.t == "Para" and #b.content == 1 and b.content[1].t == "Image"
       and nxt and nxt.t == "Para" and #nxt.content == 1 and nxt.content[1].t == "Emph" then
      local cap = nxt.content[1].content
      local num = (#cap >= 3 and cap[1].t == "Str" and cap[1].text == "Figure" and cap[3].t == "Str")
                  and cap[3].text:match("^([%dA%.]+)%.$") or nil
      if num then
        local want = in_appendix and ("A." .. (fig_count_appendix + 1)) or tostring(expect_fig)
        if num ~= want then
          io.stderr:write(("filter: figure numbered %s in the markdown is typeset as %s\n"):format(num, want))
        end
        if in_appendix then fig_count_appendix = fig_count_appendix + 1
        else expect_fig = expect_fig + 1; fig_count_body = fig_count_body + 1 end
        out:insert(make_figure(b.content[1], drop_first(cap, 4)))
        i = i + 2
        goto continue
      end
    end
    -- table: Para[Strong "Table N. ..."] followed by Table
    if b.t == "Para" and #b.content == 1 and b.content[1].t == "Strong"
       and nxt and nxt.t == "Table" then
      local cap = b.content[1].content
      if #cap >= 3 and cap[1].t == "Str" and cap[1].text == "Table" and cap[3].t == "Str"
         and cap[3].text:match("^%d+%.$") then
        out:insert(render_table(size_table(nxt), drop_first(cap, 4)))
        i = i + 2
        goto continue
      end
    end
    -- uncaptioned table (the bluntness table in §17.1)
    if b.t == "Table" then
      out:insert(render_table(size_table(b), nil))
      i = i + 1
      goto continue
    end
    -- the page-1 status banner
    if b.t == "Para" and #b.content == 1 and b.content[1].t == "Emph"
       and stringify(b.content):match("^Draft status") then
      out:insert(pandoc.RawBlock("latex", "\\begin{draftbanner}\n" ..
        inlines_to_latex(b.content[1].content) .. "\n\\end{draftbanner}"))
      i = i + 1
      goto continue
    end
    -- the author line under the title (goes to the title block)
    if b.t == "Para" and stringify(b.content):match("^Adithya Kesan Jayakanth · ") then
      i = i + 1
      goto continue
    end
    if b.t == "HorizontalRule" then i = i + 1; goto continue end
    if b.t == "RawBlock" and b.text:match("^\\clearpage\\appendix") then in_appendix = true end
    -- the one displayed formula, written as an indented code block in the markdown
    if b.t == "CodeBlock" then
      local txt = b.text:gsub("^%s+", ""):gsub("%s+$", ""):gsub("K_air", "K@AIR@")
      local s = inlines_to_latex(map_str(txt)):gsub("K@AIR@", "K\\textsubscript{air}")
      out:insert(pandoc.RawBlock("latex", "\\begin{center}\n" .. s .. "\n\\end{center}"))
      i = i + 1
      goto continue
    end
    out:insert(b)
    i = i + 1
    ::continue::
  end
  return out
end

local function Pandoc(doc)
  doc.meta.title = nil            -- the title block is titlepage.tex, not \maketitle
  io.stderr:write(("filter: %d body figures, %d appendix figures\n"):format(fig_count_body, fig_count_appendix))
  return doc
end

return {
  { Header = Header },
  { Blocks = Blocks },   -- before the inline pass, so table cells are measured on their real text
  inline_map,
  { Pandoc = Pandoc },
}
