/* ---------------------------------------------------------------------------
   Assumption panel, live Q3/Q4, scorecard, and the per-listing lookup.
   No dependencies and no build step — five people can edit this file and it
   will still work in three years.

   The three formulas are ported verbatim from four_master_questions.ipynb and
   are validated against dashboard/build/export_assets.py's regression table.
   --------------------------------------------------------------------------- */
(function () {
  'use strict';

  var ORDER = ['Antwerp', 'Amsterdam', 'LA', 'Rio'];
  var S = {};                       // loaded JSON
  var A = {};                       // live assumptions
  var CAPS = {};                    // nightly caps, user-editable

  // ------------------------------------------------------------- formulas
  function breakeven(mkt) {
    var cost = ppsqm(mkt) * A.unit;
    return (cost / A.payback / med(mkt)) / 365 * 100;
  }
  function ceiling(mkt) {
    return med(mkt) * 365 / (ppsqm(mkt) * A.unit) * 100;
  }
  function multiple(mkt) {
    return med(mkt) * A.nights / S.assumptions.markets[mkt].minwage;
  }
  function med(mkt) { return S.stats.markets[mkt].median_entire_home; }
  function ppsqm(mkt) { return S.assumptions.markets[mkt].ppsqm * A.ppsqmPct / 100; }
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
  function money(mkt, v) {
    var sym = S.stats.markets[mkt].symbol;
    return sym + v.toLocaleString('en-GB', { maximumFractionDigits: 0 });
  }
  function pct(v, d) { return v.toFixed(d === undefined ? 0 : d) + '%'; }

  // ---------------------------------------------------------- live charts
  // A horizontal bar per market, drawn as divs. Every value is printed, so
  // colour never carries meaning on its own.
  //
  // The bar is grey up to the limit and magenta beyond it. That way the
  // magenta area IS the part of the requirement the law forbids — the
  // argument is the overshoot, not the colour of the whole bar.
  function drawBars(node, spec) {
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
      if (cap !== null && !over && w(cap) - at < 4.5) at = w(cap);
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
    var max = Math.max.apply(null, vals.concat(caps, [40])) * 1.32;

    drawBars(document.getElementById('q3-chart'), {
      max: max,
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

    // The running verdict. The point of the whole section is that this
    // sentence does not change sign anywhere in the slider ranges.
    var blocked = ORDER.filter(function (m) {
      var c = capPct(m);
      return c !== null && breakeven(m) > c;
    });
    var v = document.getElementById('q3-verdict');
    v.textContent = '';
    if (blocked.length === 0) {
      v.appendChild(document.createTextNode(
        'At these settings no market’s breakeven exceeds its modelled cap. ' +
        'That takes assumptions well outside the sourced ones — check the ' +
        'cap values below.'));
    } else {
      v.appendChild(document.createTextNode('At these settings '));
      blocked.forEach(function (m, i) {
        if (i) v.appendChild(document.createTextNode(i === blocked.length - 1 ? ' and ' : ', '));
        var b = el('b', null, m + ' needs ' + pct(breakeven(m)) +
                              ' but the law allows ' + pct(capPct(m)));
        v.appendChild(b);
      });
      v.appendChild(document.createTextNode(
        '. ' + (blocked.length > 1 ? 'Those markets are' : 'That market is') +
        ' blocked by arithmetic, not by weak demand.'));
    }

    var bestCeiling = ORDER.reduce(function (a, b) {
      return ceiling(a) > ceiling(b) ? a : b;
    });
    drawBars(document.getElementById('q3-ceiling'), {
      max: Math.max.apply(null, ORDER.map(ceiling)) * 1.36,
      value: ceiling,
      hot: function (m) { return m === bestCeiling; },
      fmt: function (v) { return pct(v, 1); },
      axis: 'a full year of nights at the median rate, as a share of the property price ' +
            '— a ceiling for comparison, not an achievable return',
      alt: function () {
        return ORDER.map(function (m) {
          return m + ' ' + pct(ceiling(m), 1);
        }).join(', ');
      }
    });
  }

  function renderQ4() {
    drawBars(document.getElementById('q4-chart'), {
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

    var above = ORDER.filter(function (m) { return multiple(m) >= 1; });
    var v = document.getElementById('q4-verdict');
    v.textContent = '';
    v.appendChild(document.createTextNode('At ' + A.nights + ' nights a month, '));
    if (above.length) {
      v.appendChild(el('b', null, above.join(' and ') + ' clear' +
        (above.length === 1 ? 's' : '') + ' a local minimum wage'));
      v.appendChild(document.createTextNode(
        ' (' + above.map(function (m) { return m + ' at ' + multiple(m).toFixed(2) + '×'; })
          .join(', ') + '); the rest do not.'));
    } else {
      v.appendChild(el('b', null, 'no market clears a local minimum wage'));
      v.appendChild(document.createTextNode(
        ' — the best is ' + ORDER.reduce(function (a, b) {
          return multiple(a) > multiple(b) ? a : b;
        }) + ' at ' + Math.max.apply(null, ORDER.map(multiple)).toFixed(2) + '×.'));
    }
    v.appendChild(document.createTextNode(
      ' Nights let is the one input here a host controls directly — the ' +
      'property price and the wage are not theirs to move.'));
  }

  // ----------------------------------------------------------- scorecard
  function renderScorecard() {
    var t = document.getElementById('score-table');
    t.textContent = '';
    var cap = el('caption', 'visually-hidden',
      'Scorecard of all four master questions across the four markets');
    t.appendChild(cap);

    var thead = el('thead'), hr = el('tr');
    hr.appendChild(el('th', null, ''));
    ORDER.forEach(function (m) { hr.appendChild(el('th', null, m)); });
    thead.appendChild(hr); t.appendChild(thead);

    var rows = S.scorecard.static_rows.map(function (r) {
      return {
        label: r.label, live: false, worse: r.worse,
        get: function (m) { return r.values[m]; },
        fmt: function (v) { return r.id === 'q2' ? (v > 0 ? '+' : '') + v.toFixed(0) + '%'
                                                 : v.toFixed(0) + '% off'; }
      };
    }).concat([
      {
        label: 'Occupancy needed for payback, vs the law',
        live: true, worse: 'high',
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
        live: true, worse: 'high',
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
      tr.appendChild(el('th', null, r.label));
      var vals = ORDER.map(r.get);
      var extreme = r.worse === 'high' ? Math.max.apply(null, vals)
                                       : Math.min.apply(null, vals);
      ORDER.forEach(function (m) {
        var td = el('td');
        var hot = r.flag ? r.flag(m) : r.get(m) === extreme;
        if (hot) td.className = 'hot';
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
    var t = document.getElementById('src-table');
    t.textContent = '';
    var thead = el('thead'), hr = el('tr');
    ['Input', 'Market', 'Value', 'Where it came from'].forEach(function (h) {
      hr.appendChild(el('th', null, h));
    });
    thead.appendChild(hr); t.appendChild(thead);
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
  function cellsFor(mkt) {
    return S.cells.filter(function (c) { return c.c === mkt; });
  }

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
    var mSel = document.getElementById('t-market');
    var nSel = document.getElementById('t-nbhd');
    var rSel = document.getElementById('t-room');
    fillSelect(mSel, ORDER);

    function refreshNbhd() {
      var seen = {}, list = [];
      cellsFor(mSel.value).forEach(function (c) {
        if (!seen[c.nb]) { seen[c.nb] = 1; list.push(c.nb); }
      });
      list.sort();
      fillSelect(nSel, list, nSel.value);
      refreshRoom();
    }
    function refreshRoom() {
      var list = cellsFor(mSel.value)
        .filter(function (c) { return c.nb === nSel.value; })
        .map(function (c) { return c.rt; });
      fillSelect(rSel, list, rSel.value);
      renderTool();
    }
    mSel.addEventListener('change', refreshNbhd);
    nSel.addEventListener('change', refreshRoom);
    rSel.addEventListener('change', renderTool);
    document.getElementById('t-minnights').addEventListener('change', renderTool);
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
    var out = document.getElementById('tool-out');
    var mkt = document.getElementById('t-market').value;
    var nb = document.getElementById('t-nbhd').value;
    var rt = document.getElementById('t-room').value;
    var want = parseInt(document.getElementById('t-minnights').value, 10);
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
      left.appendChild(el('p', 'band',
        'middle half runs ' + money(mkt, c.p25) + ' – ' + money(mkt, c.p75) +
        ' · ' + (c.p75 / c.p25).toFixed(2) + '× wide'));
      left.appendChild(el('span', 'nvalue', 'n = ' + c.n + ' listings in this cell'));
      var r = el('div');
      r.appendChild(el('p', 'say', 'Local currency, never converted. This is what ' +
        c.n + ' ' + rt.toLowerCase() + ' listings in ' + nb + ' actually ask — not what ' +
        'they earn, which this dataset does not record.'));
      d.appendChild(r);
    }));

    // 2 — how much to trust it. The output that justifies the tool.
    out.appendChild(block('How much to trust it', function (left, d) {
      var r = el('div');
      if (thin) {
        left.appendChild(el('p', 'thin',
          'Only ' + c.n + ' listings here. Below ' + S.stats.trust_n +
          ' we do not print a spread — an honest blank beats a number built on ' +
          'a handful of listings.'));
        r.appendChild(el('p', 'say', 'The median above is still the best single ' +
          'guess available, but treat it as a starting point rather than a comp.'));
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
          '× apart across the middle half. Everything separating them (photos, ' +
          'the actual apartment, the host) is invisible here.'));
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
        left.appendChild(el('p', 'thin',
          'Too few listings in this cell at one or both minimum-stay settings to compare.'));
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
          '  ·  4–7 nights: ' + c.rpm4.toFixed(2) +
          '  ·  ' + (delta < 0 ? '−' : '+') + Math.abs(delta).toFixed(0) +
          '% for the longer minimum'));
        left.appendChild(el('span', 'nvalue',
          'n = ' + c.n1 + ' listings at 1 night, ' + c.n4 + ' at 4–7'));
        r.appendChild(el('p', 'say', delta < 0
          ? 'Requiring a longer stay costs this cell roughly ' +
            Math.abs(delta).toFixed(0) + '% of its booking activity — consistent with ' +
            mkt + ' overall, where the correlation is ' + st.min_stay_rho.toFixed(2) + '.'
          : 'This cell runs against the market: listings here with a longer minimum show ' +
            'more activity, not less. With ' + c.n4 + ' listings behind it, treat that as ' +
            'noise unless the cell is large.'));
        r.appendChild(el('p', 'say', 'Reviews per month is a proxy for booking activity, ' +
          'and a biased one — guests review at different rates in different markets. ' +
          'Read the direction, not the size.'));
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
        r.appendChild(el('p', 'say', 'No nightly cap is modelled for ' + mkt +
          '. That means this arithmetic is not blocked by a nights ceiling — not ' +
          'that the market is unregulated.'));
      } else if (occ > cp) {
        r.appendChild(el('p', 'thin', 'The law allows ' + pct(cp, 1) + '. At this ' +
          'neighbourhood’s prices the unit cannot repay itself legally.'));
      } else {
        r.appendChild(el('p', 'say', 'The law allows ' + pct(cp, 1) +
          ', so this cell clears its cap — unusual for ' + mkt + ', and worth ' +
          'checking against the sourced assumptions rather than the slider settings.'));
      }
      r.appendChild(el('p', 'say', 'Uses this cell’s median rather than the market’s, ' +
        'and the property price from the panel above. The property price is an ' +
        'assumption; the nightly rate is measured.'));
      d.appendChild(r);
    }));

    // 5 — income multiple for this cell
    out.appendChild(block('Income multiple for this cell', function (left, d) {
      var mult = c.p50 * A.nights / S.assumptions.markets[mkt].minwage;
      var big = el('p', 'big');
      big.appendChild(document.createTextNode(mult.toFixed(2) + '×'));
      big.appendChild(el('small', null, ' local minimum wage'));
      left.appendChild(big);
      left.appendChild(el('p', 'band', A.nights + ' nights at ' + money(mkt, c.p50) +
        ' = ' + money(mkt, Math.round(c.p50 * A.nights)) + ' gross, against ' +
        money(mkt, S.assumptions.markets[mkt].minwage) + ' a month'));
      left.appendChild(el('p', 'band', 'market median for comparison: ' +
        multiple(mkt).toFixed(2) + '×'));
      var r = el('div');
      r.appendChild(el('p', 'say', mult >= 1
        ? 'Above one minimum wage. At this level a listing is an income-generating ' +
          'asset rather than a top-up, which is the threshold that draws both ' +
          'investors and regulators.'
        : 'Below one minimum wage — supplementary income at this occupancy, ' +
          'whatever the headline nightly rate looks like.'));
      r.appendChild(el('p', 'say', 'Gross. No cleaning, platform fee, tax, vacancy or ' +
        'furnishing cost is subtracted, because none of them are in this dataset.'));
      d.appendChild(r);
    }));
  }

  // ------------------------------------------------------------- controls
  function readControls() {
    A.unit = +document.getElementById('unit').value;
    A.payback = +document.getElementById('payback').value;
    A.nights = +document.getElementById('nights').value;
    A.ppsqmPct = +document.getElementById('ppsqm').value;
    document.getElementById('unit-out').textContent = A.unit + ' m²';
    document.getElementById('payback-out').textContent = A.payback + ' yr';
    document.getElementById('nights-out').textContent = A.nights;
    document.getElementById('ppsqm-out').textContent =
      A.ppsqmPct === 100 ? 'as sourced' : (A.ppsqmPct > 100 ? '+' : '−') +
      Math.abs(A.ppsqmPct - 100) + '%';
  }

  function renderAll() {
    renderQ3();
    renderQ4();
    renderScorecard();
    renderTool();
  }

  function initCapInputs() {
    var wrap = document.getElementById('cap-inputs');
    ORDER.forEach(function (mkt) {
      var id = 'cap-' + mkt;
      var lab = el('label', null, mkt + ' — nights/year');
      lab.htmlFor = id;
      var inp = el('input');
      inp.type = 'number'; inp.id = id; inp.min = 0; inp.max = 365;
      inp.placeholder = 'no cap';
      inp.value = CAPS[mkt] === null ? '' : CAPS[mkt];
      inp.addEventListener('input', function () {
        CAPS[mkt] = inp.value === '' ? null : Math.max(0, Math.min(365, +inp.value));
        renderQ3(); renderScorecard(); renderTool();
      });
      var box = el('div');
      box.appendChild(lab); box.appendChild(inp);
      wrap.appendChild(box);
    });
  }

  function initRail() {
    var links = [].slice.call(document.querySelectorAll('#rail a'));
    if (!links.length || !('IntersectionObserver' in window)) return;
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        links.forEach(function (a) {
          a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id);
        });
      });
    }, { rootMargin: '-20% 0px -70% 0px' });
    links.forEach(function (a) {
      var t = document.querySelector(a.getAttribute('href'));
      if (t) obs.observe(t);
    });
  }

  // ---------------------------------------------------------------- boot
  Promise.all(['market_stats', 'cells', 'assumptions', 'scorecard'].map(function (f) {
    return fetch('data/' + f + '.json').then(function (r) {
      if (!r.ok) throw new Error(f + ': ' + r.status);
      return r.json();
    });
  })).then(function (res) {
    S.stats = res[0]; S.cells = res[1]; S.assumptions = res[2]; S.scorecard = res[3];
    ORDER.forEach(function (m) { CAPS[m] = S.assumptions.markets[m].cap_nights; });

    ['unit', 'payback', 'nights', 'ppsqm'].forEach(function (id) {
      document.getElementById(id).addEventListener('input', function () {
        readControls(); renderAll();
      });
    });
    document.getElementById('reset').addEventListener('click', function () {
      var d = S.assumptions.defaults;
      document.getElementById('unit').value = d.unit_size;
      document.getElementById('payback').value = d.payback_years;
      document.getElementById('nights').value = d.nights_per_month;
      document.getElementById('ppsqm').value = 100;
      ORDER.forEach(function (m) {
        CAPS[m] = S.assumptions.markets[m].cap_nights;
        var i = document.getElementById('cap-' + m);
        if (i) i.value = CAPS[m] === null ? '' : CAPS[m];
      });
      readControls(); renderAll();
    });

    initCapInputs();
    readControls();
    renderSources();
    initTool();
    renderAll();
    initRail();
  }).catch(function (err) {
    var z = document.getElementById('q3-chart');
    if (z) {
      z.textContent = 'Could not load the data files (' + err.message +
        '). This page needs to be served over HTTP — opening index.html from ' +
        'the filesystem will not work.';
    }
  });
})();
