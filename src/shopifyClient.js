const API_VERSION = process.env.SHOPIFY_API_VERSION || '2025-01';

async function adminGraphql(shop, accessToken, query, variables = {}) {
  const res = await fetch(`https://${shop}/admin/api/${API_VERSION}/graphql.json`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Shopify-Access-Token': accessToken,
    },
    body: JSON.stringify({ query, variables }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Shopify Admin API 오류 (${res.status}): ${text}`);
  }

  const json = await res.json();
  if (json.errors) {
    throw new Error(`Shopify GraphQL 오류: ${JSON.stringify(json.errors)}`);
  }
  return json.data;
}

async function fetchShopInfo(shop, accessToken) {
  const query = `
    query ShopInfo {
      shop {
        name
        myshopifyDomain
        primaryDomain { url }
        currencyCode
        email
      }
    }
  `;
  const data = await adminGraphql(shop, accessToken, query);
  return data.shop;
}

async function fetchProducts(shop, accessToken, first = 20) {
  const query = `
    query Products($first: Int!) {
      products(first: $first, sortKey: UPDATED_AT, reverse: true) {
        edges {
          node {
            id
            title
            handle
            status
            featuredImage { url altText }
            priceRangeV2 {
              minVariantPrice { amount currencyCode }
            }
          }
        }
      }
    }
  `;
  const data = await adminGraphql(shop, accessToken, query, { first });
  return data.products.edges.map((edge) => ({
    id: edge.node.id,
    title: edge.node.title,
    handle: edge.node.handle,
    status: edge.node.status,
    image: edge.node.featuredImage?.url || null,
    imageAlt: edge.node.featuredImage?.altText || edge.node.title,
    price: edge.node.priceRangeV2?.minVariantPrice?.amount || null,
    currency: edge.node.priceRangeV2?.minVariantPrice?.currencyCode || '',
  }));
}

module.exports = { fetchShopInfo, fetchProducts };
