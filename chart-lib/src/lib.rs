use plotters::prelude::*;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use serde::Deserialize;
use std::f64::consts::PI;
use std::sync::{Arc, OnceLock};
use tokio::task;
// TreeTextToPath é o trait que expõe `tree.convert_text(&fontdb)`. Nesta
// versão do usvg, o texto NÃO é resolvido dentro de `Tree::from_str` (por
// isso `Options` não tem campo `fontdb`/`font_family`) — a conversão de
// texto para paths é um passo manual e separado, feito depois do parse.
use usvg::{TreeParsing, TreeTextToPath};

// ---------------------------------------------------------------------------
// Structs for deserializing NVD/CVE JSON structures
// ---------------------------------------------------------------------------

#[derive(Deserialize, Debug, Clone)]
struct CvssData {
    #[serde(rename = "vectorString")]
    vector_string: Option<String>,
    #[serde(rename = "baseScore")]
    base_score: Option<f64>,
    #[serde(rename = "baseSeverity")]
    base_severity: Option<String>,
    #[serde(rename = "attackVector")]
    attack_vector: Option<String>,
    #[serde(rename = "attackComplexity")]
    attack_complexity: Option<String>,
    #[serde(rename = "privilegesRequired")]
    privileges_required: Option<String>,
    #[serde(rename = "userInteraction")]
    user_interaction: Option<String>,
    #[serde(rename = "confidentialityImpact")]
    confidentiality_impact: Option<String>,
    #[serde(rename = "integrityImpact")]
    integrity_impact: Option<String>,
    #[serde(rename = "availabilityImpact")]
    availability_impact: Option<String>,
}

#[derive(Deserialize, Debug)]
struct CvssMetricItem {
    #[serde(rename = "cvssData")]
    cvss_data: CvssData,
}

#[derive(Deserialize, Debug)]
struct MetricsNode {
    #[serde(rename = "cvssMetricV31")]
    cvss_metric_v31: Option<Vec<CvssMetricItem>>,
    #[serde(rename = "cvssMetricV40")]
    cvss_metric_v40: Option<Vec<CvssMetricItem>>,
}

#[derive(Deserialize, Debug)]
struct CveNode {
    id: String,
    metrics: Option<MetricsNode>,
}

#[derive(Deserialize, Debug)]
struct NvdItem {
    id: Option<String>,
    cve: Option<CveNode>,
    metrics: Option<MetricsNode>,
}

// ---------------------------------------------------------------------------
// CVSS Metrics to numeric value mappings (0.0 to 10.0)
// ---------------------------------------------------------------------------

fn map_av(val: Option<&str>) -> f64 {
    match val {
        Some("NETWORK") => 10.0,
        Some("ADJACENT_NETWORK") => 7.5,
        Some("LOCAL") => 5.0,
        Some("PHYSICAL") => 2.5,
        _ => 0.0,
    }
}

fn map_ac(val: Option<&str>) -> f64 {
    match val {
        Some("LOW") => 10.0,
        Some("HIGH") => 4.0,
        _ => 0.0,
    }
}

fn map_pr(val: Option<&str>) -> f64 {
    match val {
        Some("NONE") => 10.0,
        Some("LOW") => 5.0,
        Some("HIGH") => 2.5,
        _ => 0.0,
    }
}

fn map_ui(val: Option<&str>) -> f64 {
    match val {
        Some("NONE") => 10.0,
        Some("REQUIRED") | Some("PASSIVE") => 4.0,
        Some("ACTIVE") => 8.0,
        _ => 0.0,
    }
}

fn map_impact(val: Option<&str>) -> f64 {
    match val {
        Some("HIGH") => 10.0,
        Some("LOW") => 5.0,
        Some("NONE") => 0.0,
        _ => 0.0,
    }
}

// ---------------------------------------------------------------------------
// Image Rendering and Vector Operations
// ---------------------------------------------------------------------------

const CATEGORIES: [&str; 7] = [
    "Attack Vector (AV)",
    "Complexity (AC)",
    "Privileges (PR)",
    "User Interaction (UI)",
    "Confidentiality (C)",
    "Integrity (I)",
    "Availability (A)",
];

struct ChartData {
    cve_id: String,
    values: Vec<f64>,
    raw_labels: Vec<String>,
    vector_string: Option<String>,
    base_score: Option<f64>,
    base_severity: Option<String>,
}

fn extract_cve_and_values(json_str: &str) -> Result<ChartData, String> {
    let item: NvdItem = serde_json::from_str(json_str).map_err(|e| e.to_string())?;

    let (cve_id, metrics) = if let Some(cve) = item.cve {
        (cve.id, cve.metrics)
    } else {
        (
            item.id.unwrap_or_else(|| "CVE-UNKNOWN".to_string()),
            item.metrics,
        )
    };

    let metrics = metrics.ok_or_else(|| format!("Metrics not found for {}", cve_id))?;

    let cvss_data = if let Some(ref v31) = metrics.cvss_metric_v31 {
        v31.first().map(|m| &m.cvss_data)
    } else if let Some(ref v40) = metrics.cvss_metric_v40 {
        v40.first().map(|m| &m.cvss_data)
    } else {
        None
    }
    .ok_or_else(|| format!("CVSS metrics not found in record {}", cve_id))?
    .clone();

    let values = vec![
        map_av(cvss_data.attack_vector.as_deref()),
        map_ac(cvss_data.attack_complexity.as_deref()),
        map_pr(cvss_data.privileges_required.as_deref()),
        map_ui(cvss_data.user_interaction.as_deref()),
        map_impact(cvss_data.confidentiality_impact.as_deref()),
        map_impact(cvss_data.integrity_impact.as_deref()),
        map_impact(cvss_data.availability_impact.as_deref()),
    ];

    let raw_labels = vec![
        cvss_data.attack_vector.clone().unwrap_or_else(|| "N/A".to_string()),
        cvss_data.attack_complexity.clone().unwrap_or_else(|| "N/A".to_string()),
        cvss_data.privileges_required.clone().unwrap_or_else(|| "N/A".to_string()),
        cvss_data.user_interaction.clone().unwrap_or_else(|| "N/A".to_string()),
        cvss_data.confidentiality_impact.clone().unwrap_or_else(|| "N/A".to_string()),
        cvss_data.integrity_impact.clone().unwrap_or_else(|| "N/A".to_string()),
        cvss_data.availability_impact.clone().unwrap_or_else(|| "N/A".to_string()),
    ];

    Ok(ChartData {
        cve_id,
        values,
        raw_labels,
        vector_string: cvss_data.vector_string,
        base_score: cvss_data.base_score,
        base_severity: cvss_data.base_severity,
    })
}

fn render_svg(data: &ChartData, width: u32, height: u32) -> Result<String, String> {
    let mut svg_buffer = String::new();
    {
        let root = SVGBackend::with_string(&mut svg_buffer, (width, height)).into_drawing_area();
        root.fill(&WHITE).map_err(|e| e.to_string())?;

        let header_height = 80i32;
        let center = (
            (width / 2) as i32,
            header_height + (((height as i32) - header_height) / 2),
        );
        let radius = (width.min(height) as f64) * 0.30;
        let num_vars = CATEGORIES.len();
        let angle_step = 2.0 * PI / (num_vars as f64);

        // Nome da fonte usado dentro do próprio SVG (atributo font-family).
        // Precisa bater com uma família que exista de fato no fontdb usado
        // em `render_svg_to_png`, senão o usvg cai no fallback dele e o
        // resultado pode variar. "sans-serif" é o nome genérico do CSS/SVG
        // e o usvg sabe resolver isso sozinho para qualquer fonte sans
        // disponível no fontdb — por isso é a opção mais portátil.
        let font_family = "sans-serif";

        root.draw(&Text::new(
            format!("CVSS Metrics — {}", data.cve_id),
            (20, 18),
            (font_family, 16).into_font().style(FontStyle::Bold),
        ))
        .map_err(|e| e.to_string())?;

        let score_line = match (data.base_score, &data.base_severity) {
            (Some(score), Some(sev)) => format!("Base Score: {:.1}  |  Severity: {}", score, sev),
            (Some(score), None) => format!("Base Score: {:.1}", score),
            (None, Some(sev)) => format!("Severity: {}", sev),
            (None, None) => String::new(),
        };
        if !score_line.is_empty() {
            root.draw(&Text::new(
                score_line,
                (20, 38),
                (font_family, 12).into_font(),
            ))
            .map_err(|e| e.to_string())?;
        }

        if let Some(ref vector) = data.vector_string {
            root.draw(&Text::new(
                format!("Vector: {}", vector),
                (20, 56),
                (font_family, 11).into_font(),
            ))
            .map_err(|e| e.to_string())?;
        }

        for i in 1..=5 {
            let r = radius * (i as f64 / 5.0);
            root.draw(&Circle::new(center, r as i32, &RGBColor(200, 200, 200)))
                .map_err(|e| e.to_string())?;
        }

        let mut polygon_points = Vec::with_capacity(num_vars);

        for (idx, &val) in data.values.iter().enumerate() {
            let angle = (idx as f64 * angle_step) - (PI / 2.0);
            let cos_a = angle.cos();
            let sin_a = angle.sin();

            let axis_x = center.0 + (radius * cos_a) as i32;
            let axis_y = center.1 + (radius * sin_a) as i32;
            root.draw(&PathElement::new(
                vec![center, (axis_x, axis_y)],
                &RGBColor(220, 220, 220),
            ))
            .map_err(|e| e.to_string())?;

            let normalized = (val / 10.0).clamp(0.0, 1.0);
            let pt_r = radius * normalized;
            let pt_x = center.0 + (pt_r * cos_a) as i32;
            let pt_y = center.1 + (pt_r * sin_a) as i32;
            polygon_points.push((pt_x, pt_y));

            let label_x = center.0 + ((radius + 30.0) * cos_a) as i32;
            let label_y = center.1 + ((radius + 30.0) * sin_a) as i32;

            root.draw(&Text::new(
                CATEGORIES[idx].to_string(),
                (label_x - 45, label_y - 12),
                (font_family, 10).into_font().style(FontStyle::Bold),
            ))
            .map_err(|e| e.to_string())?;

            root.draw(&Text::new(
                data.raw_labels[idx].clone(),
                (label_x - 45, label_y + 2),
                (font_family, 10).into_font().color(&RGBColor(80, 80, 80)),
            ))
            .map_err(|e| e.to_string())?;
        }

        if !polygon_points.is_empty() {
            let mut closed_polygon = polygon_points.clone();
            closed_polygon.push(polygon_points[0]);

            root.draw(&Polygon::new(
                polygon_points,
                RGBColor(217, 83, 79).mix(0.3),
            ))
            .map_err(|e| e.to_string())?;

            root.draw(&PathElement::new(
                closed_polygon,
                ShapeStyle::from(&RGBColor(217, 83, 79)).stroke_width(2),
            ))
            .map_err(|e| e.to_string())?;
        }

        root.present().map_err(|e| e.to_string())?;
    }

    Ok(svg_buffer)
}

// ---------------------------------------------------------------------------
// Font database
// ---------------------------------------------------------------------------
//
// BUG RAIZ ORIGINAL: nesta versão do usvg, o texto só é convertido em paths
// através de `tree.convert_text(&fontdb)` (trait `TreeTextToPath`), chamado
// DEPOIS do `Tree::from_str`. Sem essa chamada, os nós de texto continuam
// como texto "cru" não resolvido e o `resvg` não desenha nada no lugar —
// por isso a imagem saía sem nenhum texto, mesmo com o SVG contendo os
// elementos <text> corretamente.
//
// Carregamos as fontes do sistema uma única vez (custa caro repetir a cada
// imagem) e cacheamos em um `OnceLock`.

fn build_fontdb() -> usvg::fontdb::Database {
    let mut db = usvg::fontdb::Database::new();
    db.load_system_fonts();
    db
}

static FONT_DB: OnceLock<usvg::fontdb::Database> = OnceLock::new();

fn get_fontdb() -> &'static usvg::fontdb::Database {
    FONT_DB.get_or_init(build_fontdb)
}

fn render_svg_to_png(svg_str: &str, width: u32, height: u32) -> Result<Vec<u8>, String> {
    let fontdb = get_fontdb();

    if fontdb.faces().count() == 0 {
        // Sem isso, o erro seria uma imagem silenciosamente sem texto —
        // preferimos falhar de forma explícita e fácil de diagnosticar.
        return Err(
            "Nenhuma fonte de sistema encontrada. Instale um pacote de fontes \
             (ex.: `fonts-dejavu-core` no Debian/Ubuntu) no ambiente onde o bot roda."
                .to_string(),
        );
    }

    let opt = usvg::Options::default();
    let mut tree = usvg::Tree::from_str(svg_str, &opt).map_err(|e| e.to_string())?;

    // Passo que faltava: converte os nós de texto em paths usando o fontdb.
    tree.convert_text(fontdb);

    let mut pixmap = tiny_skia::Pixmap::new(width, height)
        .ok_or_else(|| "Failed to allocate memory for PNG".to_string())?;

    resvg::Tree::from_usvg(&tree).render(usvg::Transform::default(), &mut pixmap.as_mut());

    pixmap.encode_png().map_err(|e| e.to_string())
}

fn process_single_json(json_str: &str, width: u32, height: u32) -> Result<(String, Vec<u8>), String> {
    let data = extract_cve_and_values(json_str)?;
    let cve_id = data.cve_id.clone();
    let svg = render_svg(&data, width, height)?;
    let png_bytes = render_svg_to_png(&svg, width, height)?;
    Ok((cve_id, png_bytes))
}

// ---------------------------------------------------------------------------
// PyO3 Class Binding
// ---------------------------------------------------------------------------

#[pyclass]
pub struct CVSSRadarChartGenerator {
    width: u32,
    height: u32,
}

#[pymethods]
impl CVSSRadarChartGenerator {
    #[new]
    #[pyo3(signature = (width=600, height=600))]
    pub fn new(width: u32, height: u32) -> Self {
        Self { width, height }
    }

    pub fn generate_chart<'py>(
        &self,
        py: Python<'py>,
        json_data: String,
    ) -> PyResult<Bound<'py, PyAny>> {
        let width = self.width;
        let height = self.height;

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let res = task::spawn_blocking(move || {
                process_single_json(&json_data, width, height)
            })
            .await
            .map_err(|e| PyValueError::new_err(e.to_string()))?
            .map_err(|e| PyValueError::new_err(e))?;

            Ok(res)
        })
    }

    pub fn generate_batch<'py>(
        &self,
        py: Python<'py>,
        json_list: Vec<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let width = self.width;
        let height = self.height;
        let json_list = Arc::new(json_list);

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let mut tasks = Vec::with_capacity(json_list.len());

            for item in json_list.iter() {
                let json_str = item.clone();
                tasks.push(task::spawn_blocking(move || {
                    process_single_json(&json_str, width, height)
                }));
            }

            let mut results = Vec::with_capacity(tasks.len());
            for task in tasks {
                match task.await {
                    Ok(Ok(data)) => results.push(data),
                    Ok(Err(e)) => eprintln!("Error generating item: {}", e),
                    Err(e) => eprintln!("Task execution error: {}", e),
                }
            }

            Ok(results)
        })
    }
}

#[pymodule]
fn chart_lib(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CVSSRadarChartGenerator>()?;
    Ok(())
}