/* ---------------------------------------------------------------------------
   Shared behaviour for all seven pages.

   No dependencies and no build step — five people can edit this file and it
   will still work in three years.

   Every page sets two attributes on <body>:
     data-page="home|q3|q4|tool|method|scorecard"   which widgets to wire up
     data-base="../"                                path back to docs/

   The Q3/Q4 formulas are ported verbatim from four_master_questions.ipynb and
   are validated against dashboard/build/export_assets.py's regression table.

   Assumption state lives in one place and survives navigation: it is written
   to localStorage on every change and mirrored into the URL query string, so
   a particular scenario can be linked to and lands on the page intact.
   --------------------------------------------------------------------------- */
(function () {
  'use strict';

  var ORDER = ['Antwerp', 'Amsterdam', 'LA', 'Rio'];
  var BODY = document.body;
  var BASE = BODY.getAttribute('data-base') || '';
  var PAGE = BODY.getAttribute('data-page') || '';
  var STORE = 'airbnb-host-assumptions-v1';

  var S = {};          // loaded JSON
  var A = {};          // live assumptions
  var CAPS = {};       // nightly caps, user-editable, null = no cap

  // ------------------------------------------------------------- formulas
  function med(mkt) { return S.stats.markets[mkt].median_entire_home; }
  function ppsqm(mkt) { return S.assumptions.markets[mkt].ppsqm * A.ppsqm / 100; }
  function breakeven(mkt) { return (ppsqm(mkt) * A.unit / A.payback / med(mkt)) / 365 * 100; }
  function ceiling(mkt) { return med(mkt) * 365 / (ppsqm(mkt) * A.unit) * 100; }
  function multiple(mkt) { return med(mkt) * A.nights / S.assumptions.markets[mkt].minwage; }
  function capPct(mkt) {
    var n = CAPS[mkt];
    return (n === null || n === undefined || n === '') ? null : n / 365 * 100;
  }

  // -------------------------------------------------------------- helpers
  function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt !== undefined) n.textContent = txt;
    return n;
  }
  function $(id) { return document.getElementById(id); }
  function money(mkt, v) {
    return S.stats.markets[mkt].symbol +
           v.toLocaleString('en-GB', { maximumFractionDigits: 0 });
  }
  function pct(v, d) { return v.toFixed(d === undefined ? 0 : d) + '%'; }
  function list(items) {          // "a", "a and b", "a, b and c"
    if (items.length < 3) return items.join(' and ');
    return items.slice(0, -1).join(', ') + ' and ' + items[items.length - 1];
  }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  // ------------------------------------------------------- shared state
  var FIELDS = ['unit', 'payback', 'nights', 'ppsqm'];

  function defaults() {
    var d = S.assumptions.defaults;
    return { unit: d.unit_size, payback: d.payback_years,
             nights: d.nights_per_month, ppsqm: 100 };
  }

  function loadState() {
    A = defaults();
    ORDER.forEach(function (m) { CAPS[m] = S.assumptions.markets[m].cap_nights; });

    var stored = null;
    try { stored = JSON.parse(localStorage.getItem(STORE) || 'null'); } catch (e) { stored = null; }
    apply(stored);

    // A query string always wins, so a shared link shows what its author saw.
    var q = {};
    (location.search || '').replace(/^\?/, '').split('&').forEach(function (kv) {
      if (!kv) return;
      var p = kv.split('=');
      q[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || '');
    });
    if (Object.keys(q).length) apply(q);
  }

  function apply(src) {
    if (!src) return;
    var r = S.assumptions.ranges;
    FIELDS.forEach(function (f) {
      var v = parseFloat(src[f]);
      if (isFinite(v)) {
        var lim = r[f === 'unit' ? 'unit_size'
                : f === 'payback' ? 'payback_years'
                : f === 'nights' ? 'nights_per_month' : 'ppsqm_pct'];
        A[f] = clamp(Math.round(v), lim[0], lim[1]);
      }
    });
    ORDER.forEach(function (m) {
      if (!(('cap_' + m) in src)) return;
      var raw = src['cap_' + m];
      if (raw === '' || raw === null) CAPS[m] = null;
      else {
        var v = parseFloat(raw);
        if (isFinite(v)) CAPS[m] = clamp(Math.round(v), 0, 365);
      }
    });
  }

  function isDefault() {
    var d = defaults();
    return FIELDS.every(function (f) { return A[f] === d[f]; }) &&
           ORDER.every(function (m) { return CAPS[m] === S.assumptions.markets[m].cap_nights; });
  }

  function saveState() {
    var out = {};
    FIELDS.forEach(function (f) { out[f] = A[f]; });
    ORDER.forEach(function (m) { out['cap_' + m] = CAPS[m] === null ? '' : CAPS[m]; });
    try { localStorage.setItem(STORE, JSON.stringify(out)); } catch (e) { /* private mode */ }

    if (!history.replaceState) return;
    var qs = isDefault() ? '' : '?' + Object.keys(out).map(function (k) {
      return encodeURIComponent(k) + '=' + encodeURIComponent(out[k]);
    }).join('&');
    history.replaceState(null, '', location.pathname + qs + location.hash);
  }

  // ---------------------------------------------------------- live charts
  // A horizontal bar per market, drawn as divs. Every value is printed, so
  // colour never carries meaning on its own.
  //
  // The bar is grey up to the limit and magenta beyond it. That way the
  // magenta area IS the part of the requirement the law forbids — the
  // argument is the overshoot, not the colour of the whole bar.
  function drawBars(node, spec) {
    if (!node) return;
    node.textContent = '';
    var max = spec.max;
    var w = function (v) { return Math.max(0, Math.min(100, v / max * 100)); };

    ORDER.forEach(function (mkt, i) {
      var v = spec.value(mkt);
      var cap = spec.cap ? spec.cap(mkt) : null;
      var over = cap !== null && v > cap;

      var row = el('div', 'row');
      row.appendChild(el('div', 'name', mkt));
      var track = el('div', 'track');

      var fill = el('div', 'fill' + (spec.hot && spec.hot(mkt) ? ' excess' : ''));
      fill.style.width = w(over ? cap : v) + '%';
      track.appendChild(fill);

      if (over) {
        var ex = el('div', 'fill excess');
        ex.style.left = w(cap) + '%';
        ex.style.width = (w(v) - w(cap)) + '%';
        track.appendChild(ex);
      }

      var val = el('div', 'val' + (over ? ' over' : ''), spec.fmt(v));
      // Nudge clear of the limit rule rather than printing the number on top
      // of it — a 2px line through a digit is worse than a few px of drift.
      var at = w(v);
      if (cap !== null && !over && w(cap) - at < 8) at = w(cap);
      val.style.left = at + '%';
      track.appendChild(val);

      if (cap !== null) {
        var m = el('div', 'cap');
        m.style.left = w(cap) + '%';
        if (!spec.capOnce || i === 0) {
          var b = el('b', null, spec.capLabel(mkt, cap));
          if (w(cap) > 62) b.className = 'left';
          m.appendChild(b);
        }
        track.appendChild(m);
      }

      row.appendChild(track);
      node.appendChild(row);
    });

    node.appendChild(el('p', 'axis', spec.axis));
    node.setAttribute('aria-label', spec.alt());
  }

  function renderQ3() {
    var vals = ORDER.map(breakeven);
    var caps = ORDER.map(capPct).filter(function (c) { return c !== null; });

    drawBars($('q3-chart'), {
      max: Math.max.apply(null, vals.concat(caps, [40])) * 1.32,
      value: breakeven,
      cap: capPct,
      fmt: function (v) { return pct(v, 1); },
      capLabel: function (mkt, c) { return 'law allows ' + pct(c, 1); },
      axis: 'occupancy needed to repay the property over ' + A.payback +
            ' years — a breakeven scenario, not a forecast',
      alt: function () {
        return ORDER.map(function (m) {
          var c = capPct(m);
          return m + ' needs ' + pct(breakeven(m), 1) + ' occupancy' +
                 (c === null ? ', no modelled cap' : ', law allows ' + pct(c, 1));
        }).join('. ');
      }
    });

    // The running verdict. The point of the whole page is that this sentence
    // does not change sign anywhere in the slider ranges.
    var blocked = ORDER.filter(function (m) {
      var c = capPct(m);
      return c !== null && breakeven(m) > c;
    });
    var v = $('q3-verdict');
    if (v) {
      v.textContent = '';
      if (!blocked.length) {
        v.appendChild(document.createTextNode(
          'At these settings no market’s breakeven exceeds its modelled cap. ' +
          'That takes assumptions well outside the sourced ones — check the cap ' +
          'values below.'));
      } else {
        v.appendChild(document.createTextNode('At these settings '));
        blocked.forEach(function (m, i) {
          if (i) v.appendChild(document.createTextNode(i === blocked.length - 1 ? ' and ' : ', '));
          v.appendChild(el('b', null, m + ' needs ' + pct(breakeven(m)) +
                                      ' but the law allows ' + pct(capPct(m))));
        });
        v.appendChild(document.createTextNode(
          '. ' + (blocked.length > 1 ? 'Those markets are' : 'That market is') +
          ' blocked by arithmetic, not by weak demand.'));
      }
    }

    var bestCeiling = ORDER.reduce(function (a, b) { return ceiling(a) > ceiling(b) ? a : b; });
    drawBars($('q3-ceiling'), {
      max: Math.max.apply(null, ORDER.map(ceiling)) * 1.36,
      value: ceiling,
      hot: function (m) { return m === bestCeiling; },
      fmt: function (v2) { return pct(v2, 1); },
      axis: 'a full year of nights at the median rate, as a share of the property price ' +
            '— a ceiling for comparison, not an achievable return',
      alt: function () {
        return ORDER.map(function (m) { return m + ' ' + pct(ceiling(m), 1); }).join(', ');
      }
    });
  }

  function renderQ4() {
    drawBars($('q4-chart'), {
      max: Math.max.apply(null, ORDER.map(multiple).concat([1.2])) * 1.34,
      value: multiple,
      cap: function () { return 1.0; },
      capOnce: true,
      fmt: function (v) { return v.toFixed(2) + '×'; },
      capLabel: function () { return 'one local minimum wage'; },
      axis: A.nights + ' nights a month at the local median entire-home rate, ' +
            'divided by that country’s monthly minimum wage',
      alt: function () {
        return ORDER.map(function (m) {
          return m + ' ' + multiple(m).toFixed(2) + ' times minimum wage';
        }).join(', ');
      }
    });

    var v = $('q4-verdict');
    if (!v) return;
    var above = ORDER.filter(function (m) { return multiple(m) >= 1; });
    v.textContent = '';
    v.appendChild(document.createTextNode('At ' + A.nights + ' nights a month, '));
    if (above.length) {
      v.appendChild(el('b', null, list(above) + ' clear' +
        (above.length === 1 ? 's' : '') + ' a local minimum wage'));
      var rest = ORDER.filter(function (m) { return multiple(m) < 1; });
      v.appendChild(document.createTextNode(' (' + list(above.map(function (m) {
        return m + ' at ' + multiple(m).toFixed(2) + '×';
      })) + ')' + (rest.length
        ? '; ' + list(rest) + (rest.length === 1 ? ' does not.' : ' do not.')
        : ' — all four.')));
    } else {
      v.appendChild(el('b', null, 'no market clears a local minimum wage'));
      v.appendChild(document.createTextNode(' — the best is ' +
        ORDER.reduce(function (a, b) { return multiple(a) > multiple(b) ? a : b; }) +
        ' at ' + Math.max.apply(null, ORDER.map(multiple)).toFixed(2) + '×.'));
    }
    v.appendChild(document.createTextNode(
      ' Nights let is the one input here a host controls directly — the property ' +
      'price and the wage are not theirs to move.'));
  }

  // ----------------------------------------------------------- scorecard
  function renderScorecard() {
    var t = $('score-table');
    if (!t) return;
    t.textContent = '';
    t.appendChild(el('caption', 'visually-hidden',
      'Scorecard of all four master questions across the four markets'));

    var thead = el('thead'), hr = el('tr');
    hr.appendChild(el('th', null, ''));
    ORDER.forEach(function (m) { hr.appendChild(el('th', null, m)); });
    thead.appendChild(hr);
    t.appendChild(thead);

    var rows = S.scorecard.static_rows.map(function (r) {
      return {
        label: r.label, href: r.id, live: false, worse: r.worse,
        get: function (m) { return r.values[m]; },
        fmt: function (v) {
          return r.id === 'q2' ? (v > 0 ? '+' : '') + v.toFixed(0) + '%' : v.toFixed(0) + '% off';
        }
      };
    }).concat([
      {
        label: 'Occupancy needed for payback, vs the law',
        href: 'q3', live: true, worse: 'high',
        get: breakeven,
        fmt: function (v) { return pct(v, 1); },
        sub: function (m) {
          var c = capPct(m);
          return c === null ? 'no modelled cap' : 'law allows ' + pct(c, 1);
        },
        flag: function (m) { var c = capPct(m); return c !== null && breakeven(m) > c; }
      },
      {
        label: 'Income as a multiple of local minimum wage',
        href: 'q4', live: true, worse: 'high',
        get: multiple,
        fmt: function (v) { return v.toFixed(2) + '×'; },
        sub: function (m) {
          return multiple(m) >= 1 ? 'clears a living wage' : 'supplementary income';
        }
      }
    ]);

    var tbody = el('tbody');
    rows.forEach(function (r) {
      var tr = el('tr', r.live ? 'live-row' : null);
      var th = el('th');
      var a = el('a', null, r.label);
      a.href = BASE + r.href + '/';
      th.appendChild(a);
      tr.appendChild(th);

      var vals = ORDER.map(r.get);
      var extreme = r.worse === 'high' ? Math.max.apply(null, vals) : Math.min.apply(null, vals);
      ORDER.forEach(function (m) {
        var td = el('td');
        if (r.flag ? r.flag(m) : r.get(m) === extreme) td.className = 'hot';
        td.appendChild(document.createTextNode(r.fmt(r.get(m))));
        if (r.sub) td.appendChild(el('span', 'sub', r.sub(m)));
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    t.appendChild(tbody);
  }

  // ------------------------------------------------------- method sources
  function renderSources() {
    var t = $('src-table');
    if (!t) return;
    t.textContent = '';
    var thead = el('thead'), hr = el('tr');
    ['Input', 'Market', 'Value', 'Where it came from'].forEach(function (h) {
      hr.appendChild(el('th', null, h));
    });
    thead.appendChild(hr);
    t.appendChild(thead);
    var tb = el('tbody');
    S.assumptions.sources.forEach(function (s) {
      var tr = el('tr');
      tr.appendChild(el('td', null, s.field));
      tr.appendChild(el('td', null, s.market));
      tr.appendChild(el('td', s.confidence === 'unverified' ? 'unverified' : null, s.value));
      tr.appendChild(el('td', null, s.source));
      tb.appendChild(tr);
    });
    t.appendChild(tb);
  }

  // ---------------------------------------------------------------- tool
  function fillSelect(sel, values, keep) {
    sel.textContent = '';
    values.forEach(function (v) {
      var o = el('option', null, v);
      o.value = v;
      sel.appendChild(o);
    });
    if (keep && values.indexOf(keep) > -1) sel.value = keep;
  }

  function initTool() {
    var mSel = $('t-market'), nSel = $('t-nbhd'), rSel = $('t-room');
    if (!mSel) return;
    fillSelect(mSel, ORDER);

    function forMarket() {
      return S.cells.filter(function (c) { return c.c === mSel.value; });
    }
    function refreshNbhd() {
      var seen = {}, list = [];
      forMarket().forEach(function (c) {
        if (!seen[c.nb]) { seen[c.nb] = 1; list.push(c.nb); }
      });
      list.sort();
      fillSelect(nSel, list, nSel.value);
      refreshRoom();
    }
    function refreshRoom() {
      fillSelect(rSel, forMarket()
        .filter(function (c) { return c.nb === nSel.value; })
        .map(function (c) { return c.rt; }), rSel.value);
      renderTool();
    }
    mSel.addEventListener('change', refreshNbhd);
    nSel.addEventListener('change', refreshRoom);
    rSel.addEventListener('change', renderTool);
    $('t-minnights').addEventListener('change', renderTool);
    refreshNbhd();
  }

  function block(title, body) {
    var d = el('div', 'out-block');
    var left = el('div');
    left.appendChild(el('h4', null, title));
    body(left, d);
    d.insertBefore(left, d.firstChild);
    return d;
  }

  function renderTool() {
    var out = $('tool-out');
    if (!out || !S.cells) return;
    var mkt = $('t-market').value, nb = $('t-nbhd').value, rt = $('t-room').value;
    var want = parseInt($('t-minnights').value, 10);
    out.textContent = '';

    var c = S.cells.filter(function (x) {
      return x.c === mkt && x.nb === nb && x.rt === rt;
    })[0];
    if (!c) return;

    var st = S.stats.markets[mkt];
    var thin = c.n < S.stats.trust_n;

    // 1 — the comp band
    out.appendChild(block('The comp band', function (left, d) {
      var big = el('p', 'big');
      big.appendChild(document.createTextNode(money(mkt, c.p50)));
      big.appendChild(el('small', null, ' per night, median'));
      left.appendChild(big);
      left.appendChild(el('p', 'band', 'middle half runs ' + money(mkt, c.p25) + ' – ' +
        money(mkt, c.p75) + ' · ' + (c.p75 / c.p25).toFixed(2) + '× wide'));
      left.appendChild(el('span', 'nvalue', 'n = ' + c.n + ' listings in this cell'));
      var r = el('div');
      r.appendChild(el('p', 'say', 'Local currency, never converted. This is what ' + c.n + ' ' +
        rt.toLowerCase() + ' listings in ' + nb + ' actually ask — not what they earn, ' +
        'which this dataset does not record.'));
      d.appendChild(r);
    }));

    // 2 — how much to trust it. The output that justifies the tool.
    out.appendChild(block('How much to trust it', function (left, d) {
      var r = el('div');
      if (thin) {
        left.appendChild(el('p', 'thin', 'Only ' + c.n + ' listings here. Below ' +
          S.stats.trust_n + ' we do not print a spread — an honest blank beats a number ' +
          'built on a handful of listings.'));
        r.appendChild(el('p', 'say', 'The median above is still the best single guess ' +
          'available, but treat it as a starting point rather than a comp.'));
      } else {
        var big = el('p', 'big');
        big.appendChild(document.createTextNode((c.p75 / c.p25).toFixed(2) + '×'));
        big.appendChild(el('small', null, ' spread, 25th to 75th percentile'));
        left.appendChild(big);
        left.appendChild(el('p', 'band', 'market-wide typical spread: ' +
          st.price_spread_ratio.toFixed(2) + '×'));
        left.appendChild(el('span', 'nvalue', 'n = ' + c.n));
        r.appendChild(el('p', 'say', 'Listings that look identical in this dataset — same ' +
          'neighbourhood, same room type — still ask ' + (c.p75 / c.p25).toFixed(2) +
          '× apart across the middle half. Everything separating them (photos, the ' +
          'actual apartment, the host) is invisible here.'));
        r.appendChild(el('p', 'say', 'That is the honest limit of a comp: it tells you the ' +
          'range you are competing in, not where in it you belong.'));
      }
      d.appendChild(r);
    }));

    // 3 — minimum-stay penalty
    out.appendChild(block('What a longer minimum stay costs', function (left, d) {
      var r = el('div');
      var have = want === 1 ? c.rpm1 : c.rpm4;
      var base = c.rpm1;
      if (base === null || have === null || c.rpm4 === null) {
        left.appendChild(el('p', 'thin', 'Too few listings in this cell at one or both ' +
          'minimum-stay settings to compare.'));
        r.appendChild(el('p', 'say', 'Across ' + mkt + ' as a whole the correlation between ' +
          'minimum nights and bookings per month is ' + st.min_stay_rho.toFixed(2) +
          ' — negative, as it is in all four markets.'));
      } else {
        var delta = (c.rpm4 - base) / (base || 1) * 100;
        var big = el('p', 'big');
        big.appendChild(document.createTextNode(have.toFixed(2)));
        big.appendChild(el('small', null, ' reviews/month at your setting'));
        left.appendChild(big);
        left.appendChild(el('p', 'band', '1-night minimum: ' + base.toFixed(2) +
          '  ·  4–7 nights: ' + c.rpm4.toFixed(2) + '  ·  ' +
          (delta < 0 ? '−' : '+') + Math.abs(delta).toFixed(0) +
          '% for the longer minimum'));
        left.appendChild(el('span', 'nvalue', 'n = ' + c.n1 + ' listings at 1 night, ' +
          c.n4 + ' at 4–7'));
        r.appendChild(el('p', 'say', delta < 0
          ? 'Requiring a longer stay costs this cell roughly ' + Math.abs(delta).toFixed(0) +
            '% of its booking activity — consistent with ' + mkt + ' overall, where the ' +
            'correlation is ' + st.min_stay_rho.toFixed(2) + '.'
          : 'This cell runs against the market: listings here with a longer minimum show ' +
            'more activity, not less, which is the opposite of the ' +
            st.min_stay_rho.toFixed(2) + ' correlation across ' + mkt + '.'));
        // The two sides of this comparison are separate slices of an already
        // small cell, so it goes thin long before the cell as a whole does.
        var thinnest = Math.min(c.n1, c.n4);
        if (thinnest < 20) {
          r.appendChild(el('p', 'say', 'Read that percentage loosely: the smaller side of the ' +
            'comparison has only ' + thinnest + ' listings. The direction is worth more than ' +
            'the size here.'));
        }
        r.appendChild(el('p', 'say', 'Reviews per month is a proxy for booking activity, and ' +
          'a biased one — guests review at different rates in different markets. Read the ' +
          'direction, not the size.'));
      }
      d.appendChild(r);
    }));

    // 4 — capital math for this cell
    out.appendChild(block('The capital math for this unit', function (left, d) {
      var cost = ppsqm(mkt) * A.unit;
      var occ = (cost / A.payback / c.p50) / 365 * 100;
      var cp = capPct(mkt);
      var big = el('p', 'big');
      big.appendChild(document.createTextNode(pct(occ, 1)));
      big.appendChild(el('small', null, ' occupancy needed'));
      left.appendChild(big);
      left.appendChild(el('p', 'band', 'a ' + A.unit + ' m² unit at ' +
        money(mkt, Math.round(ppsqm(mkt))) + '/m² = ' + money(mkt, Math.round(cost)) +
        ', repaid over ' + A.payback + ' years'));
      var r = el('div');
      if (cp === null) {
        r.appendChild(el('p', 'say', 'No nightly cap is modelled for ' + mkt + '. That means ' +
          'this arithmetic is not blocked by a nights ceiling — not that the market is ' +
          'unregulated.'));
      } else if (occ > cp) {
        r.appendChild(el('p', 'thin', 'The law allows ' + pct(cp, 1) + '. At this ' +
          'neighbourhood’s prices the unit cannot repay itself legally.'));
      } else {
        r.appendChild(el('p', 'say', 'The law allows ' + pct(cp, 1) + ', so this cell clears ' +
          'its cap — unusual for ' + mkt + ', and worth checking against the sourced ' +
          'assumptions rather than the slider settings.'));
      }
      r.appendChild(el('p', 'say', 'Uses this cell’s median rather than the market’s, ' +
        'and the property price from the panel above. The property price is an assumption; ' +
        'the nightly rate is measured.'));
      d.appendChild(r);
    }));

    // 5 — income multiple for this cell
    out.appendChild(block('Income multiple for this cell', function (left, d) {
      var mult = c.p50 * A.nights / S.assumptions.markets[mkt].minwage;
      var big = el('p', 'big');
      big.appendChild(document.createTextNode(mult.toFixed(2) + '×'));
      big.appendChild(el('small', null, ' local minimum wage'));
      left.appendChild(big);
      left.appendChild(el('p', 'band', A.nights + ' nights at ' + money(mkt, c.p50) + ' = ' +
        money(mkt, Math.round(c.p50 * A.nights)) + ' gross, against ' +
        money(mkt, S.assumptions.markets[mkt].minwage) + ' a month'));
      left.appendChild(el('p', 'band', 'market median for comparison: ' +
        multiple(mkt).toFixed(2) + '×'));
      var r = el('div');
      r.appendChild(el('p', 'say', mult >= 1
        ? 'Above one minimum wage. At this level a listing is an income-generating asset ' +
          'rather than a top-up, which is the threshold that draws both investors and regulators.'
        : 'Below one minimum wage — supplementary income at this occupancy, whatever the ' +
          'headline nightly rate looks like.'));
      r.appendChild(el('p', 'say', 'Gross. No cleaning, platform fee, tax, vacancy or ' +
        'furnishing cost is subtracted, because none of them are in this dataset.'));
      d.appendChild(r);
    }));
  }

  // ------------------------------------------------------------- controls
  var SPEC = [
    { id: 'unit', range: 'unit_size', step: 5, unit: 'm²' },
    { id: 'payback', range: 'payback_years', step: 1, unit: 'years' },
    { id: 'nights', range: 'nights_per_month', step: 1, unit: 'per month' },
    { id: 'ppsqm', range: 'ppsqm_pct', step: 5, unit: '% of sourced' }
  ];

  function syncControls() {
    SPEC.forEach(function (s) {
      var r = $(s.id), n = $(s.id + '-num');
      if (r) r.value = A[s.id];
      if (n) n.value = A[s.id];
    });
    ORDER.forEach(function (m) {
      var i = $('cap-' + m);
      if (i) i.value = CAPS[m] === null ? '' : CAPS[m];
    });
    var reset = $('reset');
    if (reset) reset.disabled = isDefault();
  }

  function initPanel() {
    var wrap = $('controls');
    if (!wrap) return;
    var ranges = S.assumptions.ranges;

    SPEC.forEach(function (s) {
      var lim = ranges[s.range];
      var ctl = el('div', 'ctl');
      var lab = el('label', null, {
        unit: 'Unit size', payback: 'Payback horizon',
        nights: 'Nights let per month', ppsqm: 'Property price per m²'
      }[s.id]);
      lab.htmlFor = s.id;
      ctl.appendChild(lab);

      var row = el('div', 'ctl-row');
      var r = el('input');
      r.type = 'range'; r.id = s.id; r.min = lim[0]; r.max = lim[1]; r.step = s.step;
      var n = el('input');
      n.type = 'number'; n.id = s.id + '-num'; n.min = lim[0]; n.max = lim[1]; n.step = s.step;
      n.setAttribute('aria-label', lab.textContent + ', exact value');
      row.appendChild(r);
      row.appendChild(n);
      ctl.appendChild(row);
      ctl.appendChild(el('span', 'unit', s.unit + ' · ' + lim[0] + '–' + lim[1]));
      wrap.appendChild(ctl);

      // The slider is for exploring, the number box for reproducing an exact
      // figure from the deck. Both write to the same state.
      r.addEventListener('input', function () {
        A[s.id] = +r.value; n.value = r.value; commit();
      });
      n.addEventListener('change', function () {
        A[s.id] = clamp(Math.round(+n.value || lim[0]), lim[0], lim[1]);
        n.value = A[s.id]; r.value = A[s.id]; commit();
      });
    });

    var capWrap = $('cap-inputs');
    if (capWrap) {
      ORDER.forEach(function (mkt) {
        var box = el('div');
        var lab = el('label', null, mkt + ' — nights/year');
        lab.htmlFor = 'cap-' + mkt;
        var inp = el('input');
        inp.type = 'number'; inp.id = 'cap-' + mkt; inp.min = 0; inp.max = 365;
        inp.placeholder = 'no cap';
        inp.addEventListener('input', function () {
          CAPS[mkt] = inp.value === '' ? null : clamp(Math.round(+inp.value), 0, 365);
          commit();
        });
        box.appendChild(lab); box.appendChild(inp);
        capWrap.appendChild(box);
      });
    }

    var reset = $('reset');
    if (reset) {
      reset.addEventListener('click', function () {
        A = defaults();
        ORDER.forEach(function (m) { CAPS[m] = S.assumptions.markets[m].cap_nights; });
        syncControls(); commit();
      });
    }

    var share = $('share');
    if (share) {
      share.addEventListener('click', function () {
        var url = location.href;
        var done = function (ok) {
          share.textContent = ok ? 'Link copied' : 'Copy failed — use the address bar';
          setTimeout(function () { share.textContent = 'Copy link to these settings'; }, 2200);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(url).then(function () { done(true); },
                                                  function () { done(false); });
        } else { done(false); }
      });
    }
  }

  function commit() {
    saveState();
    syncControls();
    render();
  }

  function render() {
    renderQ3();
    renderQ4();
    renderScorecard();
    renderTool();
  }

  // ---------------------------------------------------------------- boot
  var NEED = ['market_stats', 'assumptions', 'scorecard'];
  if (PAGE === 'tool') NEED.push('cells');   // 88 KB, and only this page uses it

  Promise.all(NEED.map(function (f) {
    return fetch(BASE + 'data/' + f + '.json').then(function (r) {
      if (!r.ok) throw new Error(f + '.json returned ' + r.status);
      return r.json();
    });
  })).then(function (res) {
    S.stats = res[0]; S.assumptions = res[1]; S.scorecard = res[2];
    if (PAGE === 'tool') S.cells = res[3];

    loadState();
    initPanel();
    syncControls();
    saveState();
    renderSources();
    initTool();
    render();
    document.querySelectorAll('.loading').forEach(function (n) { n.remove(); });
  }).catch(function (err) {
    document.querySelectorAll('.loading').forEach(function (n) {
      n.className = 'errbox';
      n.textContent = 'Could not load the data files (' + err.message + '). ' +
        'This page needs to be served over HTTP — opening index.html straight from ' +
        'the filesystem will not work.';
    });
  });
})();
