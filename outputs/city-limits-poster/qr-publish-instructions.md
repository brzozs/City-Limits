# City Limits QR Publish Status

The mobile demo is live and the poster deck now embeds a real QR code that points to the public phone demo.

## Live URL

- `https://brzozs.github.io/City-Limits/`

## Completed Steps

1. GitHub Pages was enabled for the repository and configured to build with GitHub Actions.
2. The `Deploy City Limits Mobile Demo` workflow published the `site/` folder.
3. A fresh QR code was generated for the live URL above.
4. The poster builder was rebuilt with the QR image embedded in the `Try The Game` panel.

## Outputs

- `outputs/city-limits-poster/City-Limits-Poster.pptx`
- `outputs/city-limits-poster/City-Limits-Poster-Print-Friendly.pptx`
- `outputs/city-limits-poster/output.pptx`

## Notes

- The poster builder is `build/city_limits_poster.mjs`.
- The QR asset used by the poster is `outputs/city-limits-poster/assets/play-qr.png`.
- Scratch preview and inspection artifacts live under `tmp/slides/city-limits-poster/`.
