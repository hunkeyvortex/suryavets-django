
    (function() {
      var preconnectOrigins = ["https://cdn.shopify.com"];
      var scripts = ["/cdn/shopifycloud/checkout-web/assets/c1/polyfills-legacy.CLEbs1mS.js","/cdn/shopifycloud/checkout-web/assets/c1/app-legacy.pvC1NQlC.js","/cdn/shopifycloud/checkout-web/assets/c1/esnext-vendor-legacy.DgzN_Vfv.js","/cdn/shopifycloud/checkout-web/assets/c1/context-browser-legacy.CntDl_n5.js","/cdn/shopifycloud/checkout-web/assets/c1/checkout-policy-legacy.CAUZCa4t.js","/cdn/shopifycloud/checkout-web/assets/c1/helpers-installmentsNotSupportedForAddress-legacy.DT5z-XEy.js","/cdn/shopifycloud/checkout-web/assets/c1/receipt-mapper-load-recovery-legacy.uqChrbBV.js","/cdn/shopifycloud/checkout-web/assets/c1/receipt-eager-mappers-legacy.DXleBHNu.js","/cdn/shopifycloud/checkout-web/assets/c1/consent-manager-shared-legacy.DnOvNKwN.js","/cdn/shopifycloud/checkout-web/assets/c1/sections-shared-legacy.0nunHlU4.js","/cdn/shopifycloud/checkout-web/assets/c1/error-logger-report-graphql-error-legacy.1Db_9azr.js","/cdn/shopifycloud/checkout-web/assets/c1/shop-pay-normalizeBuyerDetails-legacy.BRt4FKTA.js","/cdn/shopifycloud/checkout-web/assets/c1/helpers-derivations-legacy.vqRKHGdN.js","/cdn/shopifycloud/checkout-web/assets/c1/utilities-shopCashMoney-legacy.Cc7-NcNj.js","/cdn/shopifycloud/checkout-web/assets/c1/color-contrast-colorContrast-legacy.xUl2NPB0.js","/cdn/shopifycloud/checkout-web/assets/c1/graphql-redeemable-legacy.s-hszanz.js","/cdn/shopifycloud/checkout-web/assets/c1/hydrate-legacy.m7ywDRm4.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useShopPayExternalAppContext-legacy.DlmSzwEz.js","/cdn/shopifycloud/checkout-web/assets/c1/locale-en-legacy.cbZubmw6.js","/cdn/shopifycloud/checkout-web/assets/c1/OnePage-legacy.C0veBIcr.js","/cdn/shopifycloud/checkout-web/assets/c1/components-DeliveryTransition-legacy.Bn7sXsrY.js","/cdn/shopifycloud/checkout-web/assets/c1/useShopPayButtonClassName-legacy.BIer_nPZ.js","/cdn/shopifycloud/checkout-web/assets/c1/cross-border-hooks-legacy.D0vQnzC_.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-usePickupPoints-legacy.jEX15jrU.js","/cdn/shopifycloud/checkout-web/assets/c1/ChangeCompanyLocationLink-legacy.Br1xxcSD.js","/cdn/shopifycloud/checkout-web/assets/c1/BillingAddressForm-legacy.DABdgJA2.js","/cdn/shopifycloud/checkout-web/assets/c1/PhoneField-legacy.BkntL6FD.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useSuppressShopPayModalOnLoad-legacy.BW5tMJu5.js","/cdn/shopifycloud/checkout-web/assets/c1/components-RedirectionNotice.module-legacy.BVPLCJHP.js","/cdn/shopifycloud/checkout-web/assets/c1/Popover-legacy.425VjBQw.js","/cdn/shopifycloud/checkout-web/assets/c1/Choice-legacy.CYKXVVcq.js","/cdn/shopifycloud/checkout-web/assets/c1/Checkbox-legacy.l0GmAIBj.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useCanChangeCompanyLocation-legacy.BNvS5Hnv.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useForceShopPayUrl-legacy.CmVPhi_l.js","/cdn/shopifycloud/checkout-web/assets/c1/ImpressionEventCapture-legacy.ZYcpbn7Z.js","/cdn/shopifycloud/checkout-web/assets/c1/utilities-previous-legacy.BS3gICTx.js","/cdn/shopifycloud/checkout-web/assets/c1/CaptureEvents-ButtonWithRegisterWebPixel-legacy.CcFslMxz.js","/cdn/shopifycloud/checkout-web/assets/c1/ShopPayLogo-legacy.C7Laj0Z8.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useWalletsTimeout-legacy.DUDP8qcx.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-usePostPurchase-legacy.CDmAyAoh.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useWalletsMonorailTrack-legacy.BTa_EJeI.js","/cdn/shopifycloud/checkout-web/assets/c1/EmptyState-legacy.DTbPyqF8.js","/cdn/shopifycloud/checkout-web/assets/c1/AutocompleteField-hooks-legacy.DfVG1q0o.js","/cdn/shopifycloud/checkout-web/assets/c1/PendingShipping-legacy.DrFUEN7m.js","/cdn/shopifycloud/checkout-web/assets/c1/RememberMeSection-legacy.BURkkMHR.js","/cdn/shopifycloud/checkout-web/assets/c1/PaymentIcon-legacy.ndz4wM6U.js","/cdn/shopifycloud/checkout-web/assets/c1/cvv-cvvBridge-legacy.DY-g39xh.js","/cdn/shopifycloud/checkout-web/assets/c1/payment-usePaymentExemptionReason-legacy.BbbyeDzM.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useGeneralPaymentErrorMessage-legacy.BZxdvB2s.js","/cdn/shopifycloud/checkout-web/assets/c1/PaymentLine-legacy.w02q6dmE.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useUpdateCheckoutAddress-legacy.DoZVRpdE.js","/cdn/shopifycloud/checkout-web/assets/c1/Section-legacy.C0O_Y3SD.js","/cdn/shopifycloud/checkout-web/assets/c1/Section-SectionStyleOverride-legacy.BZtxxGir.js","/cdn/shopifycloud/checkout-web/assets/c1/PaymentErrorBanner-legacy.Be7RMOn1.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useOnePageFormSubmit-legacy.DJC34kKQ.js","/cdn/shopifycloud/checkout-web/assets/c1/PaymentButtons-legacy.Ch5-Qh3J.js","/cdn/shopifycloud/checkout-web/assets/c1/PayButton-sizing-legacy.D0PdXFUj.js","/cdn/shopifycloud/checkout-web/assets/c1/useShopPaySessionTokenStorage-legacy.vvsp1SqD.js","/cdn/shopifycloud/checkout-web/assets/c1/sandbox-helpers-legacy.bopWiXkL.js","/cdn/shopifycloud/checkout-web/assets/c1/utils-useViolationsHandler-legacy.CWMniY3p.js","/cdn/shopifycloud/checkout-web/assets/c1/checkout-as-guest-amazon-pay-legacy.Dtsk1ON_.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-payment-button-legacy.DlYSjDj3.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useShouldRevealExtension-legacy.BdQbM3Jv.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-usePreselectSpi-legacy.DZcYEIbg.js","/cdn/shopifycloud/checkout-web/assets/c1/Switch-legacy.C5KN61Zt.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useAvailableShopPromotionDiscounts-legacy.C8XWcq_6.js","/cdn/shopifycloud/checkout-web/assets/c1/Middot-legacy.Dd9Z5gq5.js","/cdn/shopifycloud/checkout-web/assets/c1/EstimatedDeliveryContent-legacy.D1EZBobd.js","/cdn/shopifycloud/checkout-web/assets/c1/shipping-methods-consolidated-included-legacy.BD_y8NUR.js","/cdn/shopifycloud/checkout-web/assets/c1/ShippingLines-legacy.dePIvCTr.js","/cdn/shopifycloud/checkout-web/assets/c1/ShipmentBreakdown-legacy.COl8VqP4.js","/cdn/shopifycloud/checkout-web/assets/c1/MerchandiseModal-legacy.xrpHmIcB.js","/cdn/shopifycloud/checkout-web/assets/c1/ShippingMethodSelector-legacy.yz6Yf6oS.js","/cdn/shopifycloud/checkout-web/assets/c1/TextArea-legacy.Dy8Dvloc.js","/cdn/shopifycloud/checkout-web/assets/c1/SubscriptionPriceBreakdown-legacy.CuSK_VEg.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useShopPayNewSignupLoginExperiment-legacy.D4e_Ai7o.js","/cdn/shopifycloud/checkout-web/assets/c1/MobileOrderSummary-legacy.Bg2yKkQy.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useStableHostMethodsReferences-legacy.CL0bST7X.js","/cdn/shopifycloud/checkout-web/assets/c1/BillingAddressSelector-legacy.DPesUf5y.js","/cdn/shopifycloud/checkout-web/assets/c1/StockProblems-StockProblemsLineItemList-legacy.CrQuMIA_.js"];
      var styles = [];
      var fontPreconnectUrls = [];
      var fontPrefetchUrls = [];
      var imgPrefetchUrls = ["https://cdn.shopify.com/s/files/1/0964/0221/1134/files/Suryavets-Logo-Pets_x320.jpg?v=1770017855"];

      function preconnect(url, callback) {
        var link = document.createElement('link');
        link.rel = 'dns-prefetch preconnect';
        link.href = url;
        link.crossOrigin = '';
        link.onload = link.onerror = callback;
        document.head.appendChild(link);
      }

      function preconnectAssets() {
        var resources = preconnectOrigins.concat(fontPreconnectUrls);
        var index = 0;
        (function next() {
          var res = resources[index++];
          if (res) preconnect(res, next);
        })();
      }

      function prefetch(url, as, callback) {
        var link = document.createElement('link');
        if (link.relList.supports('prefetch')) {
          link.rel = 'prefetch';
          link.fetchPriority = 'low';
          link.as = as;
          if (as === 'font') link.type = 'font/woff2';
          link.href = url;
          link.crossOrigin = '';
          link.onload = link.onerror = callback;
          document.head.appendChild(link);
        } else {
          var xhr = new XMLHttpRequest();
          xhr.open('GET', url, true);
          xhr.onloadend = callback;
          xhr.send();
        }
      }

      function prefetchAssets() {
        var resources = [].concat(
          scripts.map(function(url) { return [url, 'script']; }),
          styles.map(function(url) { return [url, 'style']; }),
          fontPrefetchUrls.map(function(url) { return [url, 'font']; }),
          imgPrefetchUrls.map(function(url) { return [url, 'image']; })
        );
        var index = 0;
        function run() {
          var res = resources[index++];
          if (res) prefetch(res[0], res[1], next);
        }
        var next = (self.requestIdleCallback || setTimeout).bind(self, run);
        next();
      }

      function onLoaded() {
        try {
          if (parseFloat(navigator.connection.effectiveType) > 2 && !navigator.connection.saveData) {
            preconnectAssets();
            prefetchAssets();
          }
        } catch (e) {}
      }

      if (document.readyState === 'complete') {
        onLoaded();
      } else {
        addEventListener('load', onLoaded);
      }
    })();
  