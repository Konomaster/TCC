/**
 * Source: https://gist.github.com/nkbt/9efd4facb391edbf8048
 */

module.exports = {
    "extends": "standard",
    "env": {
        "browser": true,
        "node": true,
        "es6": true
    },
    "rules": {
        // enable additional rules
        "indent": ["error", 4],
        "linebreak-style": ["error", "unix"],
        "quotes": ["error", "single", { "avoidEscape": true } ],
        "semi": ["error", "always"],
        "valid-jsdoc": ["error", { "requireParamDescription": false, "requireReturnDescription": false }],

        // override default options for rules from base configurations
        "comma-dangle": ["off"],
        "no-cond-assign": ["error", "always"],
        "space-before-function-paren": ["error", "never"],

        // disable rules from base configurations
        //"no-console": "off",

        //"prefer-arrow-callback": 0,
        //"no-var": 0
    }
};
